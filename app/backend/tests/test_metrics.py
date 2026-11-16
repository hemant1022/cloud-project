from __future__ import annotations

from fastapi.testclient import TestClient


def test_metrics_is_public(client: TestClient):
    client.get("/api/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "inventory_low_stock_products" in response.text
    assert "inventory_out_of_stock_products" in response.text
