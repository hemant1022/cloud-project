"""Aggregate inventory statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..logging_config import get_logger
from ..models import User
from ..schemas import StatsSummary
from ..services.inventory import get_summary

logger = get_logger(__name__)
router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary", response_model=StatsSummary)
def summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "viewer")),
) -> StatsSummary:
    try:
        result = get_summary(db)
        logger.info(
            "Stats served | user=%s products=%s value=%s low=%s out=%s",
            user.email,
            result.total_products,
            result.total_inventory_value,
            result.low_stock_count,
            result.out_of_stock_count,
        )
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to serve stats | user=%s", user.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not compute stats")
