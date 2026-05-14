from typing import Any

from backend.app import producer


class FakeMetadata:
    topic = "reviews"
    partition = 1
    offset = 42


class FakeFuture:
    def get(self, timeout: int) -> FakeMetadata:
        assert timeout == 10
        return FakeMetadata()


class FakeProducer:
    def __init__(self) -> None:
        self.sent: dict[str, Any] | None = None

    def send(self, topic: str, key: str, value: dict[str, Any]) -> FakeFuture:
        self.sent = {"topic": topic, "key": key, "value": value}
        return FakeFuture()


def test_send_review_publishes_to_configured_topic(monkeypatch) -> None:
    fake_producer = FakeProducer()
    event = {
        "product_id": "P001",
        "user_id": "client1",
        "score": 5,
        "text": "Great product",
    }

    monkeypatch.setattr(producer, "get_producer", lambda: fake_producer)

    metadata = producer.send_review(event)

    assert fake_producer.sent == {
        "topic": producer.settings.kafka_topic,
        "key": "P001",
        "value": event,
    }
    assert metadata == {"topic": "reviews", "partition": 1, "offset": 42}
