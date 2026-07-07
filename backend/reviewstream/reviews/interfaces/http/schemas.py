from pydantic import BaseModel, Field

from backend.reviewstream.reviews.application.commands import (
    SubmitProductReviewCommand,
    SubmitReviewCommand,
)


class ReviewIn(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=100)
    score: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1, max_length=2000)
    source: str = Field(default="web", min_length=1, max_length=50)

    def to_command(self) -> SubmitReviewCommand:
        return SubmitReviewCommand(
            product_id=self.product_id,
            user_id=self.user_id,
            score=self.score,
            text=self.text,
            source=self.source,
        )


class ProductReviewIn(BaseModel):
    score: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1, max_length=2000)

    def to_command(self, product_id: str) -> SubmitProductReviewCommand:
        return SubmitProductReviewCommand(
            product_id=product_id,
            score=self.score,
            text=self.text,
        )
