from dataclasses import dataclass
from typing import Any

from backend.reviewstream.reviews.domain.events import ReviewSubmitted


@dataclass(frozen=True)
class PublishReceipt:
    destination: str
    partition: int
    offset: int

    def to_legacy_kafka_payload(self) -> dict[str, Any]:
        return {
            "topic": self.destination,
            "partition": self.partition,
            "offset": self.offset,
        }


@dataclass(frozen=True)
class ReviewSubmissionResult:
    message: str
    publish: PublishReceipt
    review: ReviewSubmitted
