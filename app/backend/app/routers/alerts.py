"""Low-stock and out-of-stock alerts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..logging_config import get_logger
from ..models import Product, User
from ..schemas import ProductOut
from ..services.inventory import get_summary

logger = get_logger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/low-stock", response_model=list[ProductOut])
def low_stock(
    include_out_of_stock: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "viewer")),
) -> list[Product]:
    logger.debug(
        "Low-stock query | user=%s include_out=%s limit=%s",
        user.email,
        include_out_of_stock,
        limit,
    )
    stmt = select(Product).where(Product.stock_quantity <= Product.reorder_level)
    if not include_out_of_stock:
        stmt = stmt.where(Product.stock_quantity > 0)
    stmt = stmt.order_by(
        (Product.reorder_level - Product.stock_quantity).desc(),
        Product.name.asc(),
    ).limit(limit)
    items = list(db.scalars(stmt).all())
    logger.info("Low-stock alerts returned | count=%s user=%s", len(items), user.email)
    return items


@router.get("/summary")
def alerts_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "viewer")),
) -> dict:
    summary = get_summary(db)
    logger.debug("Alert summary | user=%s low=%s out=%s", user.email, summary.low_stock_count, summary.out_of_stock_count)
    return {
        "low_stock_count": summary.low_stock_count,
        "out_of_stock_count": summary.out_of_stock_count,
        "status": "ok" if summary.low_stock_count == 0 and summary.out_of_stock_count == 0 else "attention",
    }
