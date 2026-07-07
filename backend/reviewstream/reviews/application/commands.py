from dataclasses import dataclass

from backend.reviewstream.reviews.domain.models import Review


@dataclass(frozen=True)
class SubmitReviewCommand:
    product_id: str
    user_id: str
    score: int
    text: str
    source: str = "web"

    def to_review(self) -> Review:
        return Review(
            product_id=self.product_id,
            user_id=self.user_id,
            score=self.score,
            text=self.text,
            source=self.source,
        )


@dataclass(frozen=True)
class SubmitProductReviewCommand:
    product_id: str
    score: int
    text: str
    user_id: str = "web-client"
    source: str = "web"

    def to_review_command(self) -> SubmitReviewCommand:
        return SubmitReviewCommand(
            product_id=self.product_id,
            user_id=self.user_id,
            score=self.score,
            text=self.text,
            source=self.source,
        )
