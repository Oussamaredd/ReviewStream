from dataclasses import dataclass
from typing import Any

from backend.reviewstream.catalog.application.ports import ProductRepository
from backend.reviewstream.catalog.domain.models import Product


@dataclass(frozen=True)
class CatalogQueryService:
    product_repository: ProductRepository

    def list_products(self) -> list[Product]:
        return self.product_repository.list_products()

    def get_product(self, product_id: str) -> Product | None:
        return self.product_repository.get_product(product_id.strip().upper())

    def product_exists(self, product_id: str) -> bool:
        return self.get_product(product_id) is not None

    def product_name_for_id(self, product_id: str) -> str | None:
        product = self.get_product(product_id)
        if product is None:
            return None

        return product.name

    def enrich_product_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched_rows: list[dict[str, Any]] = []

        for row in rows:
            enriched = dict(row)
            product_id = str(enriched.get("product_id") or "")
            product_name = self.product_name_for_id(product_id)
            enriched["product_name"] = product_name
            enriched_rows.append(enriched)

        return enriched_rows
