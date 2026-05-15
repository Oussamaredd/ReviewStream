from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.main import app

client = TestClient(app)


def test_product_review_submission_sends_event_to_kafka(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_events: list[dict[str, Any]] = []

    def fake_send_review(event: dict[str, Any]) -> dict[str, Any]:
        sent_events.append(event)
        return {"topic": "reviews", "partition": 0, "offset": 12}

    monkeypatch.setattr(main, "send_review", fake_send_review)

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
    assert sent_events == [payload["review"]]


def test_product_review_submission_returns_404_for_unknown_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(event: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError(f"Kafka should not be called for unknown products: {event}")

    monkeypatch.setattr(main, "send_review", fail_if_called)

    response = client.post(
        "/products/UNKNOWN/reviews",
        json={"score": 5, "text": "Great product"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


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
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> None:
    def fail_if_called(event: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError(f"Kafka should not be called for invalid bodies: {event}")

    monkeypatch.setattr(main, "send_review", fail_if_called)

    response = client.post("/products/P001/reviews", json=payload)

    assert response.status_code == 422
