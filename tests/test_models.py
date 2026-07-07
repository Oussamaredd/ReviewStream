import pytest
from pydantic import ValidationError

from backend.reviewstream.reviews.domain.events import ReviewSubmitted
from backend.reviewstream.reviews.interfaces.http.schemas import ReviewIn


def test_review_in_accepts_valid_payload() -> None:
    review = ReviewIn(
        product_id="P001",
        user_id="client1",
        score=5,
        text="Great product",
    )

    assert review.product_id == "P001"
    assert review.source == "web"


@pytest.mark.parametrize(
    "payload",
    [
        {"product_id": "", "user_id": "client1", "score": 5, "text": "Great"},
        {"product_id": "P001", "user_id": "", "score": 5, "text": "Great"},
        {"product_id": "P001", "user_id": "client1", "score": 0, "text": "Great"},
        {"product_id": "P001", "user_id": "client1", "score": 6, "text": "Great"},
        {"product_id": "P001", "user_id": "client1", "score": 5, "text": ""},
    ],
)
def test_review_in_rejects_invalid_payload(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ReviewIn(**payload)


def test_review_event_adds_id_and_timestamp() -> None:
    review = ReviewIn(product_id="P001", user_id="client1", score=5, text="Great product")

    event = ReviewSubmitted.from_review(review.to_command().to_review())

    assert event.product_id == review.product_id
    assert event.review_id
    assert event.created_at.tzinfo is not None
    assert event.to_payload()["created_at"].endswith("+00:00")
