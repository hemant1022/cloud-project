"""Admin approval queue for new categories and suppliers."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..logging_config import get_logger
from ..models import CatalogRequest, Category, Supplier, User
from ..schemas import CatalogRequestOut

logger = get_logger(__name__)
router = APIRouter(prefix="/api/catalog-requests", tags=["catalog-requests"])


@router.get("", response_model=list[CatalogRequestOut])
def list_requests(
    request_status: str = Query(default="pending", alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> list[CatalogRequest]:
    if request_status not in ("pending", "approved", "rejected", "all"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter")
    stmt = select(CatalogRequest)
    if request_status != "all":
        stmt = stmt.where(CatalogRequest.status == request_status)
    items = list(db.scalars(stmt.order_by(CatalogRequest.created_at.desc())).all())
    logger.info("Catalog requests listed | status=%s count=%s admin=%s", request_status, len(items), user.email)
    return items


def _get_pending(db: Session, request_id: int) -> CatalogRequest:
    request = db.get(CatalogRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if request.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request has already been reviewed")
    return request


@router.post("/{request_id}/approve", response_model=CatalogRequestOut)
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> CatalogRequest:
    logger.info("Approve catalog request | request_id=%s admin=%s", request_id, admin.email)
    try:
        request = _get_pending(db, request_id)
        if request.kind == "category":
            existing = db.scalar(select(Category).where(func.lower(Category.name) == request.name.lower()))
            if existing is None:
                db.add(Category(name=request.name, description="Approved from CSV import request"))
                logger.info("Category approved and created | name=%s", request.name)
        else:
            existing = db.scalar(select(Supplier).where(func.lower(Supplier.name) == request.name.lower()))
            if existing is None:
                db.add(Supplier(name=request.name))
                logger.info("Supplier approved and created | name=%s", request.name)

        request.status = "approved"
        request.reviewed_by = admin.id
        request.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(request)
        logger.info("Catalog request approved | id=%s kind=%s name=%s", request.id, request.kind, request.name)
        return request
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to approve catalog request | request_id=%s", request_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not approve request")


@router.post("/{request_id}/reject", response_model=CatalogRequestOut)
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> CatalogRequest:
    logger.info("Reject catalog request | request_id=%s admin=%s", request_id, admin.email)
    try:
        request = _get_pending(db, request_id)
        request.status = "rejected"
        request.reviewed_by = admin.id
        request.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(request)
        logger.info("Catalog request rejected | id=%s kind=%s name=%s", request.id, request.kind, request.name)
        return request
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to reject catalog request | request_id=%s", request_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not reject request")
