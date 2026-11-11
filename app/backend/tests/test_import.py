from __future__ import annotations

from fastapi.testclient import TestClient

CSV_HEADER = (
    "sku,name,description,category,supplier,unit_price,cost_price,stock_quantity,reorder_level\n"
)


def _upload(client: TestClient, headers, content: str, create_missing: bool = False):
    return client.post(
        "/api/import",
        files={"file": ("products.csv", content.encode("utf-8"), "text/csv")},
        data={"create_missing": "true" if create_missing else "false"},
        headers=headers,
    )


def test_import_rejects_unknown_catalog_then_approve_and_reupload(
    client: TestClient, admin_headers, manager_headers, catalog
):
    category, _ = catalog
    csv_content = CSV_HEADER + (
        f"SKU-IMP-1,Imported Item,From CSV,{category['name']},Brand New Supplier,15.00,9.00,4,8\n"
    )

    first = _upload(client, manager_headers, csv_content)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["inserted"] == 0
    assert body["failed"] == 1
    assert body["requests_created"] == 1

    pending = client.get("/api/catalog-requests?status=pending", headers=admin_headers)
    assert pending.status_code == 200
    requests = pending.json()
    assert len(requests) == 1
    assert requests[0]["name"] == "Brand New Supplier"

    approved = client.post(
        f"/api/catalog-requests/{requests[0]['id']}/approve", headers=admin_headers
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    second = _upload(client, manager_headers, csv_content)
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["inserted"] == 1
    assert body["failed"] == 0


def test_admin_import_can_create_missing_catalog(client: TestClient, admin_headers):
    csv_content = CSV_HEADER + (
        "SKU-IMP-2,Admin Item,From CSV,New Category,New Supplier,20.00,12.00,3,6\n"
    )
    response = _upload(client, admin_headers, csv_content, create_missing=True)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["inserted"] == 1
    assert body["failed"] == 0

    categories = client.get("/api/categories", headers=admin_headers).json()
    assert any(item["name"] == "New Category" for item in categories)


def test_import_upserts_existing_sku(client: TestClient, admin_headers, catalog):
    category, supplier = catalog
    csv_content = CSV_HEADER + (
        f"SKU-IMP-3,Upserted Item,v1,{category['name']},{supplier['name']},10.00,6.00,2,5\n"
    )
    first = _upload(client, admin_headers, csv_content)
    assert first.status_code == 200
    assert first.json()["inserted"] == 1

    updated_csv = CSV_HEADER + (
        f"SKU-IMP-3,Upserted Item,v2,{category['name']},{supplier['name']},12.00,7.00,9,5\n"
    )
    second = _upload(client, admin_headers, updated_csv)
    assert second.status_code == 200
    assert second.json()["updated"] == 1
    assert second.json()["inserted"] == 0


def test_import_rejects_missing_columns(client: TestClient, admin_headers):
    response = _upload(client, admin_headers, "sku,name\nSKU-X,Only two columns\n")
    assert response.status_code == 400
