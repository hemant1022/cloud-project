"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["admin", "manager", "viewer"]
StockStatus = Literal["all", "low", "out", "in"]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=200)
    role: Role = "viewer"


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    unit_price: float = Field(default=0, ge=0)
    cost_price: float = Field(default=0, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=10, ge=0)

    @field_validator("sku", "name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    unit_price: float | None = Field(default=None, ge=0)
    cost_price: float | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    description: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    unit_price: float
    cost_price: float
    stock_quantity: int
    reorder_level: int
    inventory_value: float
    is_low_stock: bool
    is_out_of_stock: bool
    deficit: int
    created_at: datetime
    updated_at: datetime


class PaginatedProducts(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int
    pages: int


class StockAdjust(BaseModel):
    change_qty: int = Field(description="Positive to add stock, negative to remove")
    reason: Literal["RESTOCK", "SALE", "ADJUSTMENT"]
    note: str | None = None

    @field_validator("change_qty")
    @classmethod
    def non_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("change_qty must not be zero")
        return value


class BreakdownItem(BaseModel):
    name: str
    product_count: int
    inventory_value: float


class StatsSummary(BaseModel):
    total_products: int
    total_units: int
    total_inventory_value: float
    low_stock_count: int
    out_of_stock_count: int
    category_breakdown: list[BreakdownItem]
    supplier_breakdown: list[BreakdownItem]


class CatalogRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: Literal["category", "supplier"]
    name: str
    status: Literal["pending", "approved", "rejected"]
    requested_by: int | None = None
    requested_by_email: str | None = None
    reviewed_by: int | None = None
    note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class ImportErrorItem(BaseModel):
    row: int
    sku: str | None = None
    field: str | None = None
    message: str


class ImportResult(BaseModel):
    total_rows: int
    inserted: int
    updated: int
    failed: int
    requests_created: int
    errors: list[ImportErrorItem]


class Message(BaseModel):
    detail: str
