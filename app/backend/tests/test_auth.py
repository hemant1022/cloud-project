from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def test_health_is_public(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_success(client: TestClient):
    response = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "admin"


def test_login_failure(client: TestClient):
    response = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-password"})
    assert response.status_code == 401


def test_products_require_authentication(client: TestClient):
    response = client.get("/api/products")
    assert response.status_code == 401


def test_viewer_cannot_create_product(client: TestClient, viewer_headers, catalog):
    category, supplier = catalog
    response = client.post(
        "/api/products",
        json={
            "sku": "SKU-DENIED",
            "name": "Denied",
            "category_id": category["id"],
            "supplier_id": supplier["id"],
            "unit_price": 1,
            "stock_quantity": 1,
            "reorder_level": 1,
        },
        headers=viewer_headers,
    )
    assert response.status_code == 403
