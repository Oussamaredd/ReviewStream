from fastapi.testclient import TestClient

from backend.reviewstream.catalog.infrastructure.in_memory_catalog_repository import PRODUCT_CATALOG
from backend.reviewstream.main import app

client = TestClient(app)


def test_products_endpoint_returns_catalog() -> None:
    response = client.get("/products")

    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 12
    assert products[0]["product_id"] == PRODUCT_CATALOG[0].product_id
    assert products[0]["name"] == PRODUCT_CATALOG[0].name
    assert {"product_id", "name", "category", "description", "image_url", "price", "tags"}.issubset(
        products[0]
    )


def test_product_endpoint_returns_single_product() -> None:
    response = client.get("/products/P001")

    assert response.status_code == 200
    product = response.json()
    assert product["product_id"] == "P001"
    assert product["name"] == "Organic Green Tea"


def test_product_endpoint_returns_404_for_unknown_product() -> None:
    response = client.get("/products/UNKNOWN")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}
