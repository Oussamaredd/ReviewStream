from typing import Any

import pytest
from kafka.errors import KafkaTimeoutError

from backend.reviewstream.bootstrap import build_container
from backend.reviewstream.platform.config import ConfigError, Settings
from backend.reviewstream.reviews.infrastructure import kafka_review_publisher as producer


class FakeMetadata:
    topic = "reviews"
    partition = 1
    offset = 42


class FakeFuture:
    def get(self, timeout: int) -> FakeMetadata:
        assert timeout == producer.KAFKA_SEND_TIMEOUT_SECONDS
        return FakeMetadata()


class FakeProducer:
    def __init__(self) -> None:
        self.sent: dict[str, Any] | None = None

    def send(self, topic: str, key: str, value: dict[str, Any]) -> FakeFuture:
        self.sent = {"topic": topic, "key": key, "value": value}
        return FakeFuture()


def test_send_review_publishes_to_configured_topic(monkeypatch) -> None:
    publisher = producer.KafkaReviewPublisher()
    fake_producer = FakeProducer()
    event = {
        "product_id": "P001",
        "user_id": "client1",
        "score": 5,
        "text": "Great product",
    }

    monkeypatch.setattr(publisher, "get_producer", lambda connect_attempts=3: fake_producer)

    metadata = publisher.send_review(event)

    assert fake_producer.sent == {
        "topic": producer.settings.kafka_topic,
        "key": "P001",
        "value": event,
    }
    assert metadata == {"topic": "reviews", "partition": 1, "offset": 42}


def test_send_review_resets_failed_producer(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = producer.KafkaReviewPublisher()

    class FailingProducer:
        def send(self, topic: str, key: str, value: dict[str, Any]) -> None:
            raise KafkaTimeoutError("timed out")

    reset_calls = 0

    def fake_reset_producer() -> None:
        nonlocal reset_calls
        reset_calls += 1

    monkeypatch.setattr(publisher, "get_producer", lambda connect_attempts=3: FailingProducer())
    monkeypatch.setattr(publisher, "reset_producer", fake_reset_producer)

    with pytest.raises(producer.KafkaUnavailableError):
        publisher.send_review(
            {
                "product_id": "P001",
                "user_id": "client1",
                "score": 5,
                "text": "Great product",
            }
        )

    assert reset_calls == producer.KAFKA_SEND_ATTEMPTS


def test_settings_reject_empty_kafka_bootstrap_servers() -> None:
    with pytest.raises(ConfigError):
        Settings(kafka_bootstrap_servers="")


def test_settings_reject_empty_kafka_topic() -> None:
    with pytest.raises(ConfigError):
        Settings(kafka_topic=" ")


def test_kafka_probe_returns_unavailable_for_producer_configuration_error() -> None:
    def failing_producer_factory(**kwargs: Any) -> FakeProducer:
        raise ValueError("invalid Kafka client configuration")

    publisher = producer.KafkaReviewPublisher(producer_factory=failing_producer_factory)

    payload = publisher.probe()

    assert payload["status"] == "unavailable"
    assert payload["available"] is False
    assert "Kafka is unavailable" in str(payload["detail"])


def test_build_container_reads_current_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAFKA_TOPIC", "reviews-from-env")

    container = build_container()

    assert container.settings.kafka_topic == "reviews-from-env"
    container.review_publisher.close()
