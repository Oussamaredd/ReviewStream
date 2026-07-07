from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    category: str
    description: str
    image_url: str
    price: float
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        product_id = self.product_id.strip()
        name = self.name.strip()
        category = self.category.strip()
        description = self.description.strip()
        image_url = self.image_url.strip()
        tags = tuple(tag.strip() for tag in self.tags if tag.strip())

        if not product_id:
            raise ValueError("Product id is required")
        if not name:
            raise ValueError("Product name is required")
        if not category:
            raise ValueError("Product category is required")
        if self.price < 0:
            raise ValueError("Product price cannot be negative")
        if not image_url:
            raise ValueError("Product image URL is required")

        object.__setattr__(self, "product_id", product_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "image_url", image_url)
        object.__setattr__(self, "tags", tags)
