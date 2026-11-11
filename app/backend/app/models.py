"""SQLAlchemy models for the inventory application."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default="viewer")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'manager', 'viewer')", name="ck_users_role"),
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    products = relationship("Product", back_populates="category")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String(160), unique=True, nullable=False)
    contact_name = Column(String(120))
    email = Column(String(200))
    phone = Column(String(40))
    country = Column(String(80))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    products = relationship("Product", back_populates="supplier")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"))
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    cost_price = Column(Numeric(12, 2), nullable=False, default=0)
    stock_quantity = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=10)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    category = relationship("Category", back_populates="products", lazy="joined")
    supplier = relationship("Supplier", back_populates="products", lazy="joined")
    movements = relationship("StockMovement", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="ck_products_unit_price"),
        CheckConstraint("cost_price >= 0", name="ck_products_cost_price"),
        CheckConstraint("stock_quantity >= 0", name="ck_products_stock"),
        CheckConstraint("reorder_level >= 0", name="ck_products_reorder"),
    )

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None

    @property
    def supplier_name(self) -> str | None:
        return self.supplier.name if self.supplier else None

    @property
    def inventory_value(self) -> float:
        return round(float(self.unit_price or 0) * int(self.stock_quantity or 0), 2)

    @property
    def is_low_stock(self) -> bool:
        return int(self.stock_quantity or 0) <= int(self.reorder_level or 0)

    @property
    def is_out_of_stock(self) -> bool:
        return int(self.stock_quantity or 0) == 0

    @property
    def deficit(self) -> int:
        return max(int(self.reorder_level or 0) - int(self.stock_quantity or 0), 0)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    change_qty = Column(Integer, nullable=False)
    reason = Column(String(24), nullable=False)
    note = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = relationship("Product", back_populates="movements")

    __table_args__ = (
        CheckConstraint(
            "reason IN ('RESTOCK', 'SALE', 'ADJUSTMENT', 'IMPORT', 'DELETE')",
            name="ck_stock_movements_reason",
        ),
    )


class CatalogRequest(Base):
    __tablename__ = "catalog_requests"

    id = Column(Integer, primary_key=True)
    kind = Column(String(16), nullable=False)
    name = Column(String(160), nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    requested_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True))

    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        CheckConstraint("kind IN ('category', 'supplier')", name="ck_catalog_requests_kind"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_catalog_requests_status",
        ),
    )

    @property
    def requested_by_email(self) -> str | None:
        return self.requester.email if self.requester else None
