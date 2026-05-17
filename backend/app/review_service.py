from typing import Any

from backend.app.models import ReviewEvent, ReviewIn
from backend.app.producer import send_review


def queue_review(review: ReviewIn) -> dict[str, Any]:
    event = ReviewEvent.from_review(review).model_dump()
    kafka_metadata = send_review(event)

    return {
        "message": "Review sent to Kafka",
        "kafka": kafka_metadata,
        "review": event,
    }
