"""CSV product import with admin-gated catalog additions."""

from __future__ import annotations

import csv
import io
import re

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..logging_config import get_logger
from ..models import CatalogRequest, Category, Product, Supplier, User
from ..schemas import ImportErrorItem, ImportResult

logger = get_logger(__name__)

REQUIRED_COLUMNS = (
    "sku",
    "name",
    "category",
    "supplier",
    "unit_price",
    "stock_quantity",
    "reorder_level",
)

TEMPLATE_CSV = (
    "sku,name,description,category,supplier,unit_price,cost_price,stock_quantity,reorder_level\n"
    "SKU-2001,Wireless Mouse,2.4GHz ergonomic mouse,Peripherals,TechSource Ltd,24.99,15.00,120,25\n"
)

MONEY_RE = re.compile(r"[^0-9.\-]")


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def parse_money(value: str | None) -> float:
    cleaned = MONEY_RE.sub("", value or "")
    if cleaned in ("", "-", "."):
        raise ValueError("must be a valid number")
    amount = float(cleaned)
    if amount < 0:
        raise ValueError("must be zero or greater")
    return round(amount, 2)


def parse_non_negative_int(value: str | None, default: int | None = None) -> int:
    cleaned = re.sub(r"[^0-9\-]", "", value or "")
    if cleaned in ("", "-"):
        if default is not None:
            return default
        raise ValueError("must be a whole number")
    number = int(cleaned)
    if number < 0:
        raise ValueError("must be zero or greater")
    return number


def import_products(
    db: Session,
    content: bytes,
    user: User,
    create_missing: bool = False,
) -> ImportResult:
    logger.info(
        "CSV import started | user=%s role=%s bytes=%s create_missing=%s",
        user.email,
        user.role,
        len(content),
        create_missing,
    )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        logger.warning("CSV import rejected: not UTF-8 | user=%s", user.email)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must be UTF-8 encoded") from None

    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []
        headers = {normalize_header(name): name for name in fieldnames}
        missing = [column for column in REQUIRED_COLUMNS if column not in headers]
        if missing:
            logger.warning("CSV import rejected: missing columns %s | user=%s", missing, user.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing)}",
            )

        categories = {category.name.strip().lower(): category for category in db.scalars(select(Category)).all()}
        suppliers = {supplier.name.strip().lower(): supplier for supplier in db.scalars(select(Supplier)).all()}
        pending = {
            (request.kind, request.name.strip().lower())
            for request in db.scalars(
                select(CatalogRequest).where(CatalogRequest.status == "pending")
            ).all()
        }

        errors: list[ImportErrorItem] = []
        seen_skus: set[str] = set()
        total_rows = inserted = updated = failed = requests_created = 0
        admin_can_create = create_missing and user.role == "admin"

        def resolve_catalog(kind: str, name: str) -> Category | Supplier:
            nonlocal requests_created
            key = name.strip().lower()
            registry = categories if kind == "category" else suppliers
            model = Category if kind == "category" else Supplier

            existing = registry.get(key)
            if existing is not None:
                return existing

            if admin_can_create:
                entity = model(name=name.strip())
                db.add(entity)
                db.flush()
                registry[key] = entity
                logger.info("Auto-created %s during admin import | name=%s", kind, name)
                return entity

            if (kind, key) not in pending:
                db.add(
                    CatalogRequest(
                        kind=kind,
                        name=name.strip(),
                        requested_by=user.id,
                        note="Created automatically from a CSV import",
                    )
                )
                pending.add((kind, key))
                requests_created += 1
                logger.info(
                    "Catalog approval requested | kind=%s name=%s requested_by=%s",
                    kind,
                    name,
                    user.email,
                )

            raise ValueError(
                f"{kind.title()} '{name}' is not approved yet. "
                "An admin must approve the request, then re-upload the CSV."
            )

        for row_number, raw in enumerate(reader, start=2):
            total_rows += 1
            if total_rows > settings.import_max_rows:
                failed += 1
                errors.append(
                    ImportErrorItem(
                        row=row_number,
                        message=f"Row limit of {settings.import_max_rows} exceeded; remaining rows skipped",
                    )
                )
                logger.warning("CSV import row limit reached | user=%s", user.email)
                break

            sku = (raw.get(headers["sku"]) or "").strip()
            try:
                if not sku:
                    raise ValueError("sku is required")
                sku_key = sku.lower()
                if sku_key in seen_skus:
                    raise ValueError("duplicate sku within the uploaded file")
                seen_skus.add(sku_key)

                name = (raw.get(headers["name"]) or "").strip()
                if not name:
                    raise ValueError("name is required")

                category_name = (raw.get(headers["category"]) or "").strip()
                if not category_name:
                    raise ValueError("category is required")
                supplier_name = (raw.get(headers["supplier"]) or "").strip()
                if not supplier_name:
                    raise ValueError("supplier is required")

                unit_price = parse_money(raw.get(headers["unit_price"]))
                stock_quantity = parse_non_negative_int(raw.get(headers["stock_quantity"]))
                reorder_level = parse_non_negative_int(raw.get(headers.get("reorder_level", "")), default=10)
                cost_raw = raw.get(headers.get("cost_price", "")) if "cost_price" in headers else None
                cost_price = parse_money(cost_raw) if cost_raw else round(unit_price * 0.72, 2)
                description = (raw.get(headers.get("description", "")) or "").strip() or None

                category = resolve_catalog("category", category_name)
                supplier = resolve_catalog("supplier", supplier_name)

                product = db.scalar(select(Product).where(func.lower(Product.sku) == sku_key))
                if product is None:
                    product = Product(
                        sku=sku,
                        name=name,
                        description=description,
                        category_id=category.id,
                        supplier_id=supplier.id,
                        unit_price=unit_price,
                        cost_price=cost_price,
                        stock_quantity=stock_quantity,
                        reorder_level=reorder_level,
                        created_by=user.id,
                    )
                    db.add(product)
                    inserted += 1
                else:
                    product.name = name
                    product.description = description
                    product.category_id = category.id
                    product.supplier_id = supplier.id
                    product.unit_price = unit_price
                    product.cost_price = cost_price
                    product.stock_quantity = stock_quantity
                    product.reorder_level = reorder_level
                    updated += 1
            except ValueError as exc:
                failed += 1
                errors.append(ImportErrorItem(row=row_number, sku=sku or None, message=str(exc)))
                logger.warning(
                    "CSV row failed | row=%s sku=%s error=%s user=%s",
                    row_number,
                    sku or "-",
                    exc,
                    user.email,
                )
            except Exception:
                failed += 1
                errors.append(ImportErrorItem(row=row_number, sku=sku or None, message="Unexpected row error"))
                logger.exception(
                    "Unexpected CSV row error | row=%s sku=%s user=%s",
                    row_number,
                    sku or "-",
                    user.email,
                )

        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("CSV import commit failed | user=%s", user.email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Import failed; no rows were saved",
            ) from None

        result = ImportResult(
            total_rows=total_rows,
            inserted=inserted,
            updated=updated,
            failed=failed,
            requests_created=requests_created,
            errors=errors,
        )
        logger.info(
            "CSV import finished | user=%s total=%s inserted=%s updated=%s failed=%s requests=%s",
            user.email,
            result.total_rows,
            result.inserted,
            result.updated,
            result.failed,
            result.requests_created,
        )
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("CSV import failed | user=%s", user.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import failed; no rows were saved",
        ) from None
