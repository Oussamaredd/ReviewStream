from typing import Protocol

from backend.reviewstream.reviews.application.dto import PublishReceipt
from backend.reviewstream.reviews.domain.events import ReviewSubmitted


class ProductLookup(Protocol):
    def product_exists(self, product_id: str) -> bool:
        """Return whether the product exists in the catalog boundary."""


class ReviewPublisher(Protocol):
    def publish(self, event: ReviewSubmitted) -> PublishReceipt:
        """Publish a submitted review event and return transport metadata."""
