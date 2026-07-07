from dataclasses import dataclass

from backend.reviewstream.reviews.domain.errors import ReviewDomainError

MAX_PRODUCT_ID_LENGTH = 100
MAX_USER_ID_LENGTH = 100
MAX_TEXT_LENGTH = 2000
MAX_SOURCE_LENGTH = 50


@dataclass(frozen=True)
class Review:
    product_id: str
    user_id: str
    score: int
    text: str
    source: str = "web"

    def __post_init__(self) -> None:
        product_id = self.product_id.strip()
        user_id = self.user_id.strip()
        text = self.text.strip()
        source = self.source.strip()

        if not product_id:
            raise ReviewDomainError("Product id is required")
        if len(product_id) > MAX_PRODUCT_ID_LENGTH:
            raise ReviewDomainError("Product id is too long")
        if not user_id:
            raise ReviewDomainError("User id is required")
        if len(user_id) > MAX_USER_ID_LENGTH:
            raise ReviewDomainError("User id is too long")
        if not 1 <= self.score <= 5:
            raise ReviewDomainError("Review score must be between 1 and 5")
        if not text:
            raise ReviewDomainError("Review text is required")
        if len(text) > MAX_TEXT_LENGTH:
            raise ReviewDomainError("Review text is too long")
        if not source:
            raise ReviewDomainError("Review source is required")
        if len(source) > MAX_SOURCE_LENGTH:
            raise ReviewDomainError("Review source is too long")

        object.__setattr__(self, "product_id", product_id)
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "source", source)
