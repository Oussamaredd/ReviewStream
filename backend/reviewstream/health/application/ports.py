from typing import Any, Protocol


class KafkaProbe(Protocol):
    def probe(self) -> dict[str, Any]:
        """Return Kafka availability details."""


class HealthSettings(Protocol):
    @property
    def kafka_topic(self) -> str:
        """Return the Kafka topic used by the API."""
