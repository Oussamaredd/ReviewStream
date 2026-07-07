from dataclasses import dataclass

from backend.reviewstream.reviews.application.commands import (
    SubmitProductReviewCommand,
    SubmitReviewCommand,
)
from backend.reviewstream.reviews.application.dto import ReviewSubmissionResult
from backend.reviewstream.reviews.application.errors import ProductNotFoundError
from backend.reviewstream.reviews.application.ports import ProductLookup, ReviewPublisher
from backend.reviewstream.reviews.domain.events import ReviewSubmitted


@dataclass(frozen=True)
class SubmitReviewUseCase:
    review_publisher: ReviewPublisher

    def execute(self, command: SubmitReviewCommand) -> ReviewSubmissionResult:
        review = command.to_review()
        event = ReviewSubmitted.from_review(review)
        publish_receipt = self.review_publisher.publish(event)

        return ReviewSubmissionResult(
            message="Review sent to Kafka",
            publish=publish_receipt,
            review=event,
        )


@dataclass(frozen=True)
class SubmitProductReviewUseCase:
    product_lookup: ProductLookup
    submit_review: SubmitReviewUseCase

    def execute(self, command: SubmitProductReviewCommand) -> ReviewSubmissionResult:
        if not self.product_lookup.product_exists(command.product_id):
            raise ProductNotFoundError(command.product_id)

        return self.submit_review.execute(command.to_review_command())
