"""Product CRUD and stock adjustments."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..logging_config import get_logger
from ..models import Category, Product, StockMovement, Supplier, User
from ..schemas import (
    PaginatedProducts,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    StockAdjust,
    StockStatus,
)
from ..services.inventory import VALUE_EXPR, get_product_or_404

logger = get_logger(__name__)
router = APIRouter(prefix="/api/products", tags=["products"])

SORT_COLUMNS = {
    "name": Product.name,
    "sku": Product.sku,
    "unit_price": Product.unit_price,
    "stock_quantity": Product.stock_quantity,
    "inventory_value": VALUE_EXPR,
    "updated_at": Product.updated_at,
}


def _validate_references(db: Session, category_id: int | None, supplier_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")
    if supplier_id is not None and db.get(Supplier, supplier_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier not found")


@router.get("", response_model=PaginatedProducts)
def list_products(
    q: str | None = Query(default=None, max_length=120),
    category_id: int | None = None,
    supplier_id: int | None = None,
    stock_status: StockStatus = "all",
    sort: str = "name",
    order: str = "asc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "viewer")),
) -> PaginatedProducts:
    logger.debug(
        "List products | user=%s q=%s category=%s supplier=%s status=%s sort=%s order=%s page=%s size=%s",
        user.email,
        q,
        category_id,
        supplier_id,
        stock_status,
        sort,
        order,
        page,
        page_size,
    )
    try:
        stmt = select(Product)
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.description.ilike(pattern),
                )
            )
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if supplier_id is not None:
            stmt = stmt.where(Product.supplier_id == supplier_id)
        if stock_status == "low":
            stmt = stmt.where(Product.stock_quantity <= Product.reorder_level, Product.stock_quantity > 0)
        elif stock_status == "out":
            stmt = stmt.where(Product.stock_quantity == 0)
        elif stock_status == "in":
            stmt = stmt.where(Product.stock_quantity > Product.reorder_level)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        sort_column = SORT_COLUMNS.get(sort, Product.name)
        ordering = desc(sort_column) if order.lower() == "desc" else asc(sort_column)
        items = list(
            db.scalars(
                stmt.order_by(ordering, Product.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        pages = math.ceil(total / page_size) if total else 0
        logger.debug("List products result | total=%s returned=%s", total, len(items))
        return PaginatedProducts(items=items, total=total, page=page, page_size=page_size, pages=pages)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list products")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not list products")


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
) -> Product:
    logger.info("Create product | sku=%s user=%s", payload.sku, user.email)
    try:
        duplicate = db.scalar(select(Product).where(func.lower(Product.sku) == payload.sku.lower()))
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A product with that SKU already exists")
        _validate_references(db, payload.category_id, payload.supplier_id)

        product = Product(**payload.model_dump(), created_by=user.id)
        db.add(product)
        db.commit()
        db.refresh(product)
        logger.info("Product created | id=%s sku=%s", product.id, product.sku)
        return product
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to create product | sku=%s", payload.sku)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create product")


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "viewer")),
) -> Product:
    return get_product_or_404(db, product_id)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
) -> Product:
    logger.info("Update product | product_id=%s user=%s", product_id, user.email)
    try:
        product = get_product_or_404(db, product_id)
        data = payload.model_dump(exclude_unset=True)

        if "sku" in data and data["sku"]:
            duplicate = db.scalar(
                select(Product).where(
                    func.lower(Product.sku) == data["sku"].lower(),
                    Product.id != product_id,
                )
            )
            if duplicate is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another product uses that SKU")
        if "category_id" in data or "supplier_id" in data:
            _validate_references(
                db,
                data.get("category_id", product.category_id),
                data.get("supplier_id", product.supplier_id),
            )

        for field, value in data.items():
            setattr(product, field, value)
        db.commit()
        db.refresh(product)
        logger.info("Product updated | id=%s sku=%s fields=%s", product.id, product.sku, sorted(data))
        return product
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to update product | product_id=%s", product_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update product")


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    logger.info("Delete product | product_id=%s user=%s", product_id, user.email)
    try:
        product = get_product_or_404(db, product_id)
        db.delete(product)
        db.commit()
        logger.info("Product deleted | id=%s sku=%s", product_id, product.sku)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to delete product | product_id=%s", product_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete product")


@router.post("/{product_id}/adjust", response_model=ProductOut)
def adjust_stock(
    product_id: int,
    payload: StockAdjust,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
) -> Product:
    logger.info(
        "Adjust stock | product_id=%s change=%s reason=%s user=%s",
        product_id,
        payload.change_qty,
        payload.reason,
        user.email,
    )
    try:
        product = get_product_or_404(db, product_id)
        new_quantity = int(product.stock_quantity) + payload.change_qty
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adjustment would make stock negative (current={product.stock_quantity})",
            )

        product.stock_quantity = new_quantity
        db.add(
            StockMovement(
                product_id=product.id,
                change_qty=payload.change_qty,
                reason=payload.reason,
                note=payload.note,
                created_by=user.id,
            )
        )
        db.commit()
        db.refresh(product)
        logger.info(
            "Stock adjusted | id=%s sku=%s new_quantity=%s",
            product.id,
            product.sku,
            product.stock_quantity,
        )
        return product
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to adjust stock | product_id=%s", product_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not adjust stock")
