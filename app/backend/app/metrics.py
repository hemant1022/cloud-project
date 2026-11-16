"""Prometheus gauges backed by inventory data."""

from __future__ import annotations

from prometheus_client import Gauge
from sqlalchemy.orm import Session

from .logging_config import get_logger
from .services.inventory import get_stock_counts

logger = get_logger(__name__)

LOW_STOCK_PRODUCTS = Gauge(
    "inventory_low_stock_products",
    "Products at or below reorder level with stock remaining",
)
OUT_OF_STOCK_PRODUCTS = Gauge(
    "inventory_out_of_stock_products",
    "Products with zero stock",
)


def update_inventory_gauges(db: Session) -> None:
    low_stock, out_of_stock = get_stock_counts(db)
    LOW_STOCK_PRODUCTS.set(low_stock)
    OUT_OF_STOCK_PRODUCTS.set(out_of_stock)
    logger.debug(
        "Inventory metrics refreshed | low_stock=%s out_of_stock=%s",
        low_stock,
        out_of_stock,
    )
