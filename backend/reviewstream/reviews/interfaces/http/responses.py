from pydantic import BaseModel

from backend.reviewstream.reviews.application.dto import ReviewSubmissionResult


class KafkaPublishResponse(BaseModel):
    topic: str
    partition: int
    offset: int


class ReviewEventResponse(BaseModel):
    product_id: str
    user_id: str
    score: int
    text: str
    source: str
    review_id: str
    created_at: str


class ReviewSubmissionResponse(BaseModel):
    message: str
    kafka: KafkaPublishResponse
    review: ReviewEventResponse

    @classmethod
    def from_result(cls, result: ReviewSubmissionResult) -> "ReviewSubmissionResponse":
        return cls(
            message=result.message,
            kafka=KafkaPublishResponse(**result.publish.to_legacy_kafka_payload()),
            review=ReviewEventResponse(
                product_id=result.review.product_id,
                user_id=result.review.user_id,
                score=result.review.score,
                text=result.review.text,
                source=result.review.source,
                review_id=result.review.review_id,
                created_at=result.review.created_at.isoformat(),
            ),
        )

    def to_payload(self) -> dict[str, object]:
        return self.model_dump()
