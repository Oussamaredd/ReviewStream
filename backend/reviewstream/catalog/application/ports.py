from typing import Protocol

from backend.reviewstream.catalog.domain.models import Product


class ProductRepository(Protocol):
    def list_products(self) -> list[Product]:
        """Return all products known to the catalog."""

    def get_product(self, product_id: str) -> Product | None:
        """Return a product by id, or None when unknown."""
