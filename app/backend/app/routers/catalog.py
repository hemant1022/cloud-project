"""Category and supplier catalog management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..logging_config import get_logger
from ..models import Category, Supplier, User
from ..schemas import CategoryCreate, CategoryOut, SupplierCreate, SupplierOut

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "viewer")),
) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> Category:
    name = payload.name.strip()
    logger.info("Create category | name=%s user=%s", name, user.email)
    try:
        existing = db.scalar(select(Category).where(func.lower(Category.name) == name.lower()))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")
        category = Category(name=name, description=payload.description)
        db.add(category)
        db.commit()
        db.refresh(category)
        logger.info("Category created | id=%s name=%s", category.id, category.name)
        return category
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        logger.warning("Category uniqueness conflict | name=%s", name)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists") from None
    except Exception:
        db.rollback()
        logger.exception("Failed to create category | name=%s", name)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create category")


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    logger.info("Delete category | category_id=%s user=%s", category_id, user.email)
    try:
        category = db.get(Category, category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        db.delete(category)
        db.commit()
        logger.info("Category deleted | id=%s", category_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to delete category | category_id=%s", category_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete category")


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "viewer")),
) -> list[Supplier]:
    return list(db.scalars(select(Supplier).order_by(Supplier.name)).all())


@router.post("/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> Supplier:
    name = payload.name.strip()
    logger.info("Create supplier | name=%s user=%s", name, user.email)
    try:
        existing = db.scalar(select(Supplier).where(func.lower(Supplier.name) == name.lower()))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Supplier already exists")
        supplier = Supplier(
            name=name,
            contact_name=payload.contact_name,
            email=payload.email,
            phone=payload.phone,
            country=payload.country,
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
        logger.info("Supplier created | id=%s name=%s", supplier.id, supplier.name)
        return supplier
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        logger.warning("Supplier uniqueness conflict | name=%s", name)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Supplier already exists") from None
    except Exception:
        db.rollback()
        logger.exception("Failed to create supplier | name=%s", name)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create supplier")


@router.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    logger.info("Delete supplier | supplier_id=%s user=%s", supplier_id, user.email)
    try:
        supplier = db.get(Supplier, supplier_id)
        if supplier is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
        db.delete(supplier)
        db.commit()
        logger.info("Supplier deleted | id=%s", supplier_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to delete supplier | supplier_id=%s", supplier_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete supplier")
