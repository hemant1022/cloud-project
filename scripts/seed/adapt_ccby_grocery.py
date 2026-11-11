#!/usr/bin/env python3
"""Adapt the CC BY 4.0 Grocery Inventory dataset into inventory seed CSVs.

The script is intentionally dependency-free (stdlib only) so it can run before
the backend environment exists.

Example:
    py -3.12 scripts/seed/adapt_ccby_grocery.py \
        --input app/db/seed/raw/Grocery_Inventory_and_Sales_Dataset.csv \
        --limit 120 --seed 42
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "app" / "backend" / "app"))

from logging_config import configure_logger, get_logger  # noqa: E402

PRODUCT_FIELDS = [
    "sku",
    "name",
    "description",
    "category",
    "supplier",
    "unit_price",
    "cost_price",
    "stock_quantity",
    "reorder_level",
]

ALIASES = {
    "sku": ("product_id", "sku", "id"),
    "name": ("product_name", "name", "product"),
    "category": ("category", "product_category"),
    "supplier": ("supplier_name", "supplier", "vendor"),
    "unit_price": ("unit_price", "price", "selling_price"),
    "stock_quantity": ("stock_quantity", "stock", "quantity"),
    "reorder_level": ("reorder_level", "reorder_point", "minimum_stock_level"),
    "status": ("status", "inventory_status"),
}

MONEY_RE = re.compile(r"[^0-9.\-]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Raw Kaggle CSV")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "app" / "db" / "seed",
        help="Where categories/suppliers/products CSVs are written",
    )
    parser.add_argument("--limit", type=int, default=120, help="Number of products to keep")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    return parser.parse_args()


def normalize(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")


def build_column_map(fieldnames: list[str]) -> dict[str, str]:
    normalized = {normalize(name): name for name in fieldnames}
    mapping: dict[str, str] = {}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[field] = normalized[alias]
                break
    return mapping


def parse_int(value: str | None, default: int = 0) -> int:
    if value is None or not str(value).strip():
        return default
    cleaned = re.sub(r"[^0-9\-]", "", str(value))
    return int(cleaned) if cleaned not in ("", "-") else default


def parse_money(value: str | None) -> float:
    if value is None or not str(value).strip():
        return 0.0
    cleaned = MONEY_RE.sub("", str(value))
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def load_rows(path: Path) -> tuple[list[dict], dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Input CSV has no header row")
        column_map = build_column_map(reader.fieldnames)
        missing = [field for field in ("sku", "name", "category", "supplier", "unit_price", "stock_quantity") if field not in column_map]
        if missing:
            raise ValueError(
                "Input CSV is missing required columns: "
                + ", ".join(missing)
                + f". Found headers: {reader.fieldnames}"
            )
        rows = []
        reorder_column = column_map.get("reorder_level")
        for raw in reader:
            record = {
                "sku": (raw.get(column_map["sku"]) or "").strip(),
                "name": (raw.get(column_map["name"]) or "").strip(),
                "category": (raw.get(column_map["category"]) or "").strip(),
                "supplier": (raw.get(column_map["supplier"]) or "").strip(),
                "unit_price": parse_money(raw.get(column_map["unit_price"])),
                "stock_quantity": parse_int(raw.get(column_map["stock_quantity"])),
                "reorder_level": parse_int(raw.get(reorder_column), 10) if reorder_column else 10,
                "status": (raw.get(column_map["status"]) or "").strip() if "status" in column_map else "",
            }
            if not record["sku"] or not record["name"]:
                continue
            if not record["category"]:
                record["category"] = "Uncategorized"
            if not record["supplier"]:
                record["supplier"] = "Unknown Supplier"
            record["cost_price"] = round(record["unit_price"] * 0.72, 2)
            record["description"] = f"Imported {record['category']} item from CC BY 4.0 grocery dataset"
            rows.append(record)
    return rows, column_map


def is_out_of_stock(row: dict) -> bool:
    status = row.get("status", "").lower()
    return row["stock_quantity"] <= 0 or "out" in status


def is_low_stock(row: dict) -> bool:
    status = row.get("status", "").lower()
    return not is_out_of_stock(row) and (
        row["stock_quantity"] <= row["reorder_level"] or "low" in status
    )


def select_rows(rows: list[dict], limit: int, rng: random.Random) -> list[dict]:
    selected: list[dict] = []
    seen: set[str] = set()

    def add(row: dict) -> None:
        if row["sku"] not in seen and len(selected) < limit:
            selected.append(row)
            seen.add(row["sku"])

    for row in rows:
        if is_out_of_stock(row):
            add(row)
        if sum(is_out_of_stock(r) for r in selected) >= 4:
            break

    for row in rows:
        if is_low_stock(row):
            add(row)
        if sum(is_low_stock(r) for r in selected) >= 15:
            break

    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["sku"] not in seen:
            by_category[row["category"]].append(row)

    for group in by_category.values():
        rng.shuffle(group)

    while len(selected) < limit and any(by_category.values()):
        for category in sorted(by_category):
            if by_category[category]:
                add(by_category[category].pop())

    return selected


def write_products(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRODUCT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in PRODUCT_FIELDS})


def write_categories(path: Path, rows: list[dict]) -> None:
    categories = sorted({row["category"] for row in rows})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "description"])
        for name in categories:
            writer.writerow([name, f"{name} items imported from CC BY 4.0 grocery dataset"])


def write_suppliers(path: Path, rows: list[dict]) -> None:
    suppliers = sorted({row["supplier"] for row in rows})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "contact_name", "email", "phone", "country"])
        for name in suppliers:
            writer.writerow([name, "", "", "", ""])


def main() -> int:
    args = parse_args()
    configure_logger(stack="backend", force=True)
    log = get_logger("seed.adapter")

    log.info("Seed adaptation started | input=%s limit=%s seed=%s", args.input, args.limit, args.seed)
    if not args.input.exists():
        log.error("Input CSV not found: %s", args.input)
        return 2

    try:
        rows, column_map = load_rows(args.input)
        log.info("Loaded %s source rows | columns=%s", len(rows), column_map)
        if not rows:
            log.error("No valid product rows found in %s", args.input)
            return 1

        rng = random.Random(args.seed)
        selected = select_rows(rows, args.limit, rng)
        args.output_dir.mkdir(parents=True, exist_ok=True)

        write_products(args.output_dir / "products.csv", selected)
        write_categories(args.output_dir / "categories.csv", selected)
        write_suppliers(args.output_dir / "suppliers.csv", selected)

        low = sum(is_low_stock(row) for row in selected)
        out = sum(is_out_of_stock(row) for row in selected)
        log.info(
            "Seed adaptation finished | products=%s categories=%s suppliers=%s low_stock=%s out_of_stock=%s",
            len(selected),
            len({row["category"] for row in selected}),
            len({row["supplier"] for row in selected}),
            low,
            out,
        )
        log.info("Wrote seed files to %s", args.output_dir.resolve())
        return 0
    except Exception:
        log.exception("Seed adaptation failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
