from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=100)
    score: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1, max_length=2000)
    source: str = Field(default="web", max_length=50)


class ProductReviewIn(BaseModel):
    score: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1, max_length=2000)


class ReviewEvent(ReviewIn):
    review_id: str
    created_at: str

    @classmethod
    def from_review(cls, review: ReviewIn) -> "ReviewEvent":
        return cls(
            **review.model_dump(),
            review_id=str(uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
