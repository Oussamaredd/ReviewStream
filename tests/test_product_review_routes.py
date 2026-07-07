from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.reviewstream.bootstrap import build_container, create_app
from backend.reviewstream.health.application.checks import HealthService
from backend.reviewstream.health.infrastructure.kafka_health_probe import KafkaHealthProbe
from backend.reviewstream.reviews.application.dto import PublishReceipt
from backend.reviewstream.reviews.application.use_cases import (
    SubmitProductReviewUseCase,
    SubmitReviewUseCase,
)
from backend.reviewstream.reviews.domain.events import ReviewSubmitted


class FakeReviewPublisher:
    def __init__(self) -> None:
        self.sent_events: list[dict[str, object]] = []

    def publish(self, event: ReviewSubmitted) -> PublishReceipt:
        self.sent_events.append(event.to_payload())
        return PublishReceipt(destination="reviews", partition=0, offset=12)

    def probe(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "available": True,
            "bootstrap_servers": ["127.0.0.1:9092"],
            "topic": "reviews",
        }

    def close(self) -> None:
        return None


@pytest.fixture
def fake_publisher() -> FakeReviewPublisher:
    return FakeReviewPublisher()


@pytest.fixture
def client(fake_publisher: FakeReviewPublisher) -> TestClient:
    container = build_container()
    container.review_publisher = fake_publisher
    container.submit_review = SubmitReviewUseCase(fake_publisher)
    container.submit_product_review = SubmitProductReviewUseCase(
        container.catalog_service, container.submit_review
    )
    container.health_service = HealthService(
        settings=container.settings,
        kafka_probe=KafkaHealthProbe(fake_publisher.probe),
    )
    return TestClient(create_app(container))


def test_product_review_submission_sends_event_to_kafka(
    client: TestClient,
    fake_publisher: FakeReviewPublisher,
) -> None:
    response = client.post(
        "/products/P001/reviews",
        json={"score": 5, "text": "Great product, fresh and tasty."},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["message"] == "Review sent to Kafka"
    assert payload["kafka"] == {"topic": "reviews", "partition": 0, "offset": 12}
    assert payload["review"]["product_id"] == "P001"
    assert payload["review"]["user_id"] == "web-client"
    assert payload["review"]["source"] == "web"
    assert payload["review"]["score"] == 5
    assert payload["review"]["text"] == "Great product, fresh and tasty."
    assert payload["review"]["review_id"]
    assert payload["review"]["created_at"]
    assert fake_publisher.sent_events == [payload["review"]]


def test_product_review_submission_returns_404_for_unknown_product(
    client: TestClient,
    fake_publisher: FakeReviewPublisher,
) -> None:
    response = client.post(
        "/products/UNKNOWN/reviews",
        json={"score": 5, "text": "Great product"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}
    assert fake_publisher.sent_events == []


@pytest.mark.parametrize(
    "payload",
    [
        {"score": 0, "text": "Great product"},
        {"score": 6, "text": "Great product"},
        {"score": 5, "text": ""},
        {"score": 5},
        {"text": "Great product"},
    ],
)
def test_product_review_submission_rejects_invalid_body(
    client: TestClient,
    fake_publisher: FakeReviewPublisher,
    payload: dict[str, Any],
) -> None:
    response = client.post("/products/P001/reviews", json=payload)

    assert response.status_code == 422
    assert fake_publisher.sent_events == []
