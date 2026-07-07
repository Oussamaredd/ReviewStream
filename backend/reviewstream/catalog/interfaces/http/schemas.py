from pydantic import BaseModel, Field

from backend.reviewstream.catalog.domain.models import Product


class ProductResponse(BaseModel):
    product_id: str
    name: str
    category: str
    description: str
    image_url: str
    price: float = Field(..., ge=0)
    tags: list[str]

    @classmethod
    def from_domain(cls, product: Product) -> "ProductResponse":
        return cls(
            product_id=product.product_id,
            name=product.name,
            category=product.category,
            description=product.description,
            image_url=product.image_url,
            price=product.price,
            tags=list(product.tags),
        )
