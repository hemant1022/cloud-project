from __future__ import annotations

from fastapi.testclient import TestClient


def _create_product(client: TestClient, headers, catalog, sku="SKU-0001", stock=5, reorder=10, price=10.0):
    category, supplier = catalog
    response = client.post(
        "/api/products",
        json={
            "sku": sku,
            "name": "Test Product",
            "description": "A product for tests",
            "category_id": category["id"],
            "supplier_id": supplier["id"],
            "unit_price": price,
            "cost_price": 6.0,
            "stock_quantity": stock,
            "reorder_level": reorder,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_product_crud(client: TestClient, admin_headers, catalog):
    product = _create_product(client, admin_headers, catalog)
    assert product["sku"] == "SKU-0001"
    assert product["is_low_stock"] is True
    assert product["inventory_value"] == 50.0
    assert product["category_name"] == "Test Category"

    listing = client.get("/api/products", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    detail = client.get(f"/api/products/{product['id']}", headers=admin_headers)
    assert detail.status_code == 200

    updated = client.patch(
        f"/api/products/{product['id']}",
        json={"unit_price": 12.5, "name": "Updated Product"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["unit_price"] == 12.5
    assert updated.json()["name"] == "Updated Product"

    deleted = client.delete(f"/api/products/{product['id']}", headers=admin_headers)
    assert deleted.status_code == 204

    missing = client.get(f"/api/products/{product['id']}", headers=admin_headers)
    assert missing.status_code == 404


def test_stats_and_alerts(client: TestClient, admin_headers, catalog):
    _create_product(client, admin_headers, catalog, sku="SKU-STAT-1", stock=5, reorder=10, price=10.0)

    summary = client.get("/api/stats/summary", headers=admin_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_products"] == 1
    assert body["total_units"] == 5
    assert body["total_inventory_value"] == 50.0
    assert body["low_stock_count"] == 1
    assert body["out_of_stock_count"] == 0
    assert body["category_breakdown"][0]["name"] == "Test Category"

    alerts = client.get("/api/alerts/low-stock", headers=admin_headers)
    assert alerts.status_code == 200
    assert len(alerts.json()) == 1
    assert alerts.json()[0]["deficit"] == 5


def test_stock_adjustment(client: TestClient, admin_headers, catalog):
    product = _create_product(client, admin_headers, catalog, sku="SKU-ADJ-1", stock=5, reorder=10)

    restock = client.post(
        f"/api/products/{product['id']}/adjust",
        json={"change_qty": 25, "reason": "RESTOCK", "note": "weekly restock"},
        headers=admin_headers,
    )
    assert restock.status_code == 200
    assert restock.json()["stock_quantity"] == 30
    assert restock.json()["is_low_stock"] is False

    negative = client.post(
        f"/api/products/{product['id']}/adjust",
        json={"change_qty": -1000, "reason": "SALE"},
        headers=admin_headers,
    )
    assert negative.status_code == 400
