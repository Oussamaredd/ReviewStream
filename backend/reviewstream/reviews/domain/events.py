from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from backend.reviewstream.reviews.domain.models import Review


def new_review_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ReviewSubmitted:
    product_id: str
    user_id: str
    score: int
    text: str
    source: str
    review_id: str
    created_at: datetime

    @classmethod
    def from_review(
        cls,
        review: Review,
        *,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> "ReviewSubmitted":
        if id_factory is None:
            id_factory = new_review_id
        if clock is None:
            clock = utc_now

        return cls(
            product_id=review.product_id,
            user_id=review.user_id,
            score=review.score,
            text=review.text,
            source=review.source,
            review_id=id_factory().strip(),
            created_at=clock(),
        )

    def to_payload(self) -> dict[str, object]:
        if not self.review_id:
            raise ValueError("Review event id is required")

        return {
            "product_id": self.product_id,
            "user_id": self.user_id,
            "score": self.score,
            "text": self.text,
            "source": self.source,
            "review_id": self.review_id,
            "created_at": self.created_at.isoformat(),
        }
