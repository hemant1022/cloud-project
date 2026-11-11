"""Inventory queries and aggregates."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..logging_config import get_logger
from ..models import Category, Product, Supplier
from ..schemas import BreakdownItem, StatsSummary

logger = get_logger(__name__)

VALUE_EXPR = Product.unit_price * Product.stock_quantity


def get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        logger.warning("Product not found | product_id=%s", product_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def _breakdown(db: Session, join_model, fk_column, empty_label: str) -> list[BreakdownItem]:
    label = func.coalesce(join_model.name, empty_label)
    stmt = (
        select(
            label,
            func.count(Product.id),
            func.coalesce(func.sum(VALUE_EXPR), 0),
        )
        .select_from(Product)
        .outerjoin(join_model, fk_column == join_model.id)
        .group_by(label)
        .order_by(func.coalesce(func.sum(VALUE_EXPR), 0).desc())
    )
    return [
        BreakdownItem(name=name, product_count=count, inventory_value=round(float(value or 0), 2))
        for name, count, value in db.execute(stmt).all()
    ]


def get_summary(db: Session) -> StatsSummary:
    try:
        total_products = db.scalar(select(func.count(Product.id))) or 0
        total_units = db.scalar(select(func.coalesce(func.sum(Product.stock_quantity), 0))) or 0
        total_value = db.scalar(select(func.coalesce(func.sum(VALUE_EXPR), 0))) or 0
        low_stock = (
            db.scalar(
                select(func.count(Product.id)).where(
                    Product.stock_quantity <= Product.reorder_level,
                    Product.stock_quantity > 0,
                )
            )
            or 0
        )
        out_of_stock = (
            db.scalar(select(func.count(Product.id)).where(Product.stock_quantity == 0)) or 0
        )
        summary = StatsSummary(
            total_products=int(total_products),
            total_units=int(total_units),
            total_inventory_value=round(float(total_value), 2),
            low_stock_count=int(low_stock),
            out_of_stock_count=int(out_of_stock),
            category_breakdown=_breakdown(db, Category, Product.category_id, "Uncategorized"),
            supplier_breakdown=_breakdown(db, Supplier, Product.supplier_id, "No supplier"),
        )
        logger.debug(
            "Stats computed | products=%s units=%s value=%s low=%s out=%s",
            summary.total_products,
            summary.total_units,
            summary.total_inventory_value,
            summary.low_stock_count,
            summary.out_of_stock_count,
        )
        return summary
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to compute inventory summary")
        raise
