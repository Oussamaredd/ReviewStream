import json
import logging
from threading import Lock
import time
from typing import Any, Callable

from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from backend.reviewstream.platform.config import Settings, settings
from backend.reviewstream.reviews.application.dto import PublishReceipt
from backend.reviewstream.reviews.application.errors import ReviewPublishUnavailableError
from backend.reviewstream.reviews.domain.events import ReviewSubmitted

logger = logging.getLogger(__name__)

KAFKA_CONNECT_ATTEMPTS = 3
KAFKA_CONNECT_RETRY_DELAY_SECONDS = 0.5
KAFKA_SEND_ATTEMPTS = 2
KAFKA_SEND_TIMEOUT_SECONDS = 5


class KafkaUnavailableError(RuntimeError):
    """Raised when the local API cannot reach Kafka."""


def serialize_value(value: Any) -> bytes:
    return json.dumps(value).encode("utf-8")


def serialize_key(key: str | None) -> bytes | None:
    return key.encode("utf-8") if key else None


class KafkaReviewPublisher:
    def __init__(
        self,
        app_settings: Settings | None = None,
        producer_factory: Callable[..., KafkaProducer] = KafkaProducer,
    ) -> None:
        self.settings = app_settings or settings
        self.producer_factory = producer_factory
        self._producer: KafkaProducer | None = None
        self._producer_lock = Lock()

    def publish(self, event: ReviewSubmitted) -> PublishReceipt:
        try:
            metadata = self.send_review(event.to_payload())
        except KafkaUnavailableError as error:
            raise ReviewPublishUnavailableError(str(error)) from error

        return PublishReceipt(
            destination=str(metadata["topic"]),
            partition=int(metadata["partition"]),
            offset=int(metadata["offset"]),
        )

    def close(self) -> None:
        self.reset_producer()

    def configured_bootstrap_servers(self) -> list[str]:
        return [
            server.strip()
            for server in self.settings.kafka_bootstrap_servers.split(",")
            if server.strip()
        ]

    def kafka_unavailable_message(self) -> str:
        bootstrap_servers = ", ".join(self.configured_bootstrap_servers()) or "<none configured>"
        return (
            f"Kafka is unavailable at {bootstrap_servers}. "
            "Start Kafka with `make docker-up`, wait for it with `make kafka-wait`, "
            "and create the topic with `make kafka-topic`."
        )

    def _producer_config(self) -> dict[str, Any]:
        return {
            "bootstrap_servers": self.configured_bootstrap_servers(),
            "value_serializer": serialize_value,
            "key_serializer": serialize_key,
            "acks": "all",
            "retries": 3,
            "retry_backoff_ms": 300,
            "request_timeout_ms": 4000,
            "max_block_ms": 4000,
            "api_version_auto_timeout_ms": 2000,
            "metadata_max_age_ms": 10000,
        }

    def _close_producer_instance(self, producer: KafkaProducer) -> None:
        try:
            producer.flush(timeout=KAFKA_SEND_TIMEOUT_SECONDS)
            producer.close(timeout=KAFKA_SEND_TIMEOUT_SECONDS)
        except Exception as error:  # pragma: no cover - defensive cleanup path
            logger.debug("Kafka producer cleanup failed: %s", error)

    def _close_producer_unlocked(self) -> None:
        if self._producer is None:
            return

        try:
            self._close_producer_instance(self._producer)
        finally:
            self._producer = None

    def reset_producer(self) -> None:
        with self._producer_lock:
            self._close_producer_unlocked()

    def get_producer(self, connect_attempts: int = KAFKA_CONNECT_ATTEMPTS) -> KafkaProducer:
        if not self.configured_bootstrap_servers():
            raise KafkaUnavailableError(self.kafka_unavailable_message())

        with self._producer_lock:
            if self._producer is not None:
                if self._producer.bootstrap_connected():
                    return self._producer

                logger.warning("Kafka producer lost its bootstrap connection; reconnecting")
                self._close_producer_unlocked()

        attempts = max(1, connect_attempts)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                new_producer = self.producer_factory(**self._producer_config())
                with self._producer_lock:
                    if self._producer is None:
                        self._producer = new_producer
                        return new_producer
                    if self._producer.bootstrap_connected():
                        existing_producer = self._producer
                    else:
                        self._close_producer_unlocked()
                        self._producer = new_producer
                        return new_producer

                self._close_producer_instance(new_producer)
                return existing_producer
            except (NoBrokersAvailable, KafkaError, OSError, TypeError, ValueError) as error:
                last_error = error
                logger.warning(
                    "Kafka is not ready at %s. Retry %s/%s",
                    ", ".join(self.configured_bootstrap_servers()),
                    attempt,
                    attempts,
                )
                if attempt < attempts:
                    time.sleep(KAFKA_CONNECT_RETRY_DELAY_SECONDS)

        raise KafkaUnavailableError(self.kafka_unavailable_message()) from last_error

    def send_review(self, event: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(1, KAFKA_SEND_ATTEMPTS + 1):
            producer = self.get_producer(
                connect_attempts=KAFKA_CONNECT_ATTEMPTS if attempt == 1 else 1
            )

            try:
                future = producer.send(
                    self.settings.kafka_topic,
                    key=str(event["product_id"]),
                    value=event,
                )
                metadata = future.get(timeout=KAFKA_SEND_TIMEOUT_SECONDS)

                return {
                    "topic": metadata.topic,
                    "partition": metadata.partition,
                    "offset": metadata.offset,
                }
            except (KafkaError, KeyError, TypeError, ValueError) as error:
                last_error = error
                logger.warning(
                    "Kafka send failed on attempt %s/%s; resetting producer: %s",
                    attempt,
                    KAFKA_SEND_ATTEMPTS,
                    error,
                )
                self.reset_producer()

        raise KafkaUnavailableError(self.kafka_unavailable_message()) from last_error

    def probe(self) -> dict[str, Any]:
        try:
            producer = self.get_producer(connect_attempts=1)
            available = producer.bootstrap_connected()
            return {
                "status": "ok" if available else "unavailable",
                "available": available,
                "bootstrap_servers": self.configured_bootstrap_servers(),
                "topic": self.settings.kafka_topic,
            }
        except KafkaUnavailableError as error:
            return {
                "status": "unavailable",
                "available": False,
                "bootstrap_servers": self.configured_bootstrap_servers(),
                "topic": self.settings.kafka_topic,
                "detail": str(error),
            }


_default_publisher = KafkaReviewPublisher()


def configured_bootstrap_servers() -> list[str]:
    return _default_publisher.configured_bootstrap_servers()


def kafka_unavailable_message() -> str:
    return _default_publisher.kafka_unavailable_message()


def get_producer(connect_attempts: int = KAFKA_CONNECT_ATTEMPTS) -> KafkaProducer:
    return _default_publisher.get_producer(connect_attempts=connect_attempts)


def reset_producer() -> None:
    _default_publisher.reset_producer()


def send_review(event: dict[str, Any]) -> dict[str, Any]:
    return _default_publisher.send_review(event)


def probe_kafka() -> dict[str, Any]:
    return _default_publisher.probe()


def close_producer() -> None:
    _default_publisher.close()
