from typing import Any

from pydantic import BaseModel, Field


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    description: str
    image_url: str
    price: float = Field(..., ge=0)
    tags: list[str]


PRODUCT_CATALOG: tuple[Product, ...] = (
    Product(
        product_id="P001",
        name="Organic Green Tea",
        category="Tea",
        description="Light sencha-style green tea with a clean grassy finish.",
        image_url=(
            "https://images.unsplash.com/photo-1544787219-7f47ccb76574"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=12.99,
        tags=["organic", "caffeine", "pantry"],
    ),
    Product(
        product_id="P002",
        name="Premium Coffee Beans",
        category="Coffee",
        description="Small-batch roasted beans with chocolate and citrus notes.",
        image_url=(
            "https://images.unsplash.com/photo-1447933601403-0c6688de566e"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=18.5,
        tags=["whole bean", "breakfast", "roasted"],
    ),
    Product(
        product_id="P003",
        name="Dark Chocolate Box",
        category="Sweets",
        description="Assorted dark chocolate squares with sea salt and almond.",
        image_url=(
            "https://images.unsplash.com/photo-1606312619070-d48b4c652a52"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=16.0,
        tags=["gift", "cocoa", "dessert"],
    ),
    Product(
        product_id="P004",
        name="Almond Butter",
        category="Spreads",
        description="Creamy roasted almond butter with no added refined sugar.",
        image_url=(
            "https://images.unsplash.com/photo-1621939514649-280e2ee25f60"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=9.75,
        tags=["protein", "spread", "vegan"],
    ),
    Product(
        product_id="P005",
        name="Protein Granola",
        category="Breakfast",
        description="Crunchy oat clusters with seeds, nuts, and plant protein.",
        image_url=(
            "https://images.unsplash.com/photo-1517093157656-b9eccef91cb1"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=8.4,
        tags=["breakfast", "protein", "crunchy"],
    ),
    Product(
        product_id="P006",
        name="Olive Oil",
        category="Pantry",
        description="Cold-pressed extra virgin olive oil for finishing and cooking.",
        image_url=(
            "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=22.0,
        tags=["extra virgin", "cooking", "imported"],
    ),
    Product(
        product_id="P007",
        name="Honey Jar",
        category="Pantry",
        description="Wildflower honey with a mellow floral sweetness.",
        image_url=(
            "https://images.unsplash.com/photo-1587049352846-4a222e784d38"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=10.25,
        tags=["sweetener", "wildflower", "tea"],
    ),
    Product(
        product_id="P008",
        name="Spicy Chips",
        category="Snacks",
        description="Kettle-cooked chips dusted with smoky chili seasoning.",
        image_url=(
            "https://images.unsplash.com/photo-1566478989037-eec170784d0b"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=4.5,
        tags=["snack", "spicy", "party"],
    ),
    Product(
        product_id="P009",
        name="Pasta Pack",
        category="Pantry",
        description="Bronze-cut pasta that holds rich sauces and bakes well.",
        image_url=(
            "https://images.unsplash.com/photo-1551462147-ff29053bfc14"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=6.2,
        tags=["dinner", "family", "semolina"],
    ),
    Product(
        product_id="P010",
        name="Dog Treats",
        category="Pet",
        description="Oven-baked peanut butter treats for everyday rewards.",
        image_url=(
            "https://images.unsplash.com/photo-1589924691995-400dc9ecc119"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=7.8,
        tags=["pet", "baked", "training"],
    ),
    Product(
        product_id="P011",
        name="Herbal Infusion",
        category="Tea",
        description="Caffeine-free mint, chamomile, and citrus peel blend.",
        image_url=(
            "https://images.unsplash.com/photo-1563911892437-1feda0179e1b"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=11.5,
        tags=["caffeine-free", "herbal", "evening"],
    ),
    Product(
        product_id="P012",
        name="Breakfast Cereal",
        category="Breakfast",
        description="Toasted whole-grain cereal with dried berries and flakes.",
        image_url=(
            "https://images.unsplash.com/photo-1521483451569-e33803c0330c"
            "?auto=format&fit=crop&w=900&q=80"
        ),
        price=5.95,
        tags=["whole grain", "berries", "family"],
    ),
)

PRODUCTS_BY_ID: dict[str, Product] = {product.product_id: product for product in PRODUCT_CATALOG}


def list_products() -> list[dict[str, Any]]:
    return [product.model_dump() for product in PRODUCT_CATALOG]


def get_product(product_id: str) -> Product | None:
    return PRODUCTS_BY_ID.get(product_id)


def product_name_for_id(product_id: str) -> str | None:
    product = get_product(product_id)
    if product is None:
        return None

    return product.name


def enrich_product_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched_rows: list[dict[str, Any]] = []

    for row in rows:
        enriched = dict(row)
        product_id = str(enriched.get("product_id") or "")
        product_name = product_name_for_id(product_id)
        if product_name:
            enriched["product_name"] = product_name
        enriched_rows.append(enriched)

    return enriched_rows
