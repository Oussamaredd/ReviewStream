from fastapi import APIRouter, HTTPException

from backend.reviewstream.catalog.application.queries import CatalogQueryService
from backend.reviewstream.catalog.interfaces.http.schemas import ProductResponse


def create_router(catalog_service: CatalogQueryService) -> APIRouter:
    router = APIRouter(tags=["catalog"])

    @router.get("/products", response_model=list[ProductResponse])
    def get_products() -> list[ProductResponse]:
        return [ProductResponse.from_domain(product) for product in catalog_service.list_products()]

    @router.get("/products/{product_id}", response_model=ProductResponse)
    def get_catalog_product(product_id: str) -> ProductResponse:
        product = catalog_service.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        return ProductResponse.from_domain(product)

    return router
