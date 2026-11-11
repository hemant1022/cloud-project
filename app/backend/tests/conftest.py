from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TMP_DIR = Path(tempfile.mkdtemp(prefix="inventory-tests-"))
TEST_DB = TMP_DIR / "test_inventory.db"

os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB.as_posix()}")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "adminpass123")
os.environ.setdefault("LOG_DIR", str(TMP_DIR / "logs"))
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CatalogRequest, Category, Product, StockMovement, Supplier, User  # noqa: E402

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_inventory_data():
    yield
    db = SessionLocal()
    try:
        db.query(StockMovement).delete()
        db.query(Product).delete()
        db.query(CatalogRequest).delete()
        db.query(Category).delete()
        db.query(Supplier).delete()
        db.query(User).filter(User.email != ADMIN_EMAIL).delete()
        db.commit()
    finally:
        db.close()


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(login(client, ADMIN_EMAIL, ADMIN_PASSWORD))


@pytest.fixture()
def manager_headers(client: TestClient, admin_headers: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/auth/users",
        json={"email": "manager@test.local", "password": "managerpass123", "role": "manager"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return auth_headers(login(client, "manager@test.local", "managerpass123"))


@pytest.fixture()
def viewer_headers(client: TestClient, admin_headers: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/auth/users",
        json={"email": "viewer@test.local", "password": "viewerpass123", "role": "viewer"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return auth_headers(login(client, "viewer@test.local", "viewerpass123"))


@pytest.fixture()
def catalog(client: TestClient, admin_headers: dict[str, str]) -> tuple[dict, dict]:
    category = client.post(
        "/api/categories",
        json={"name": "Test Category", "description": "Category for tests"},
        headers=admin_headers,
    )
    supplier = client.post(
        "/api/suppliers",
        json={"name": "Test Supplier", "country": "United States"},
        headers=admin_headers,
    )
    assert category.status_code == 201, category.text
    assert supplier.status_code == 201, supplier.text
    return category.json(), supplier.json()
