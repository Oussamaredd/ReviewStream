import json
import logging
from threading import Lock
import time
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from .config import settings

_producer: KafkaProducer | None = None
_producer_lock = Lock()
logger = logging.getLogger(__name__)

KAFKA_CONNECT_ATTEMPTS = 3
KAFKA_CONNECT_RETRY_DELAY_SECONDS = 0.5
KAFKA_SEND_ATTEMPTS = 2
KAFKA_SEND_TIMEOUT_SECONDS = 5


class KafkaUnavailableError(RuntimeError):
    """Raised when the local API cannot reach Kafka."""


def configured_bootstrap_servers() -> list[str]:
    return [
        server.strip() for server in settings.kafka_bootstrap_servers.split(",") if server.strip()
    ]


def kafka_unavailable_message() -> str:
    bootstrap_servers = ", ".join(configured_bootstrap_servers()) or "<none configured>"
    return (
        f"Kafka is unavailable at {bootstrap_servers}. "
        "Start Kafka with `make docker-up`, wait for it with `make kafka-wait`, "
        "and create the topic with `make kafka-topic`."
    )


def _producer_config() -> dict[str, Any]:
    return {
        "bootstrap_servers": configured_bootstrap_servers(),
        "value_serializer": lambda value: json.dumps(value).encode("utf-8"),
        "key_serializer": lambda key: key.encode("utf-8") if key else None,
        "acks": "all",
        "retries": 3,
        "retry_backoff_ms": 300,
        "request_timeout_ms": 4000,
        "max_block_ms": 4000,
        "api_version_auto_timeout_ms": 2000,
        "metadata_max_age_ms": 10000,
    }


def _close_producer_unlocked() -> None:
    global _producer

    if _producer is None:
        return

    try:
        _producer.flush(timeout=KAFKA_SEND_TIMEOUT_SECONDS)
        _producer.close(timeout=KAFKA_SEND_TIMEOUT_SECONDS)
    except Exception as error:  # pragma: no cover - defensive cleanup path
        logger.debug("Kafka producer cleanup failed: %s", error)
    finally:
        _producer = None


def reset_producer() -> None:
    with _producer_lock:
        _close_producer_unlocked()


def get_producer(connect_attempts: int = KAFKA_CONNECT_ATTEMPTS) -> KafkaProducer:
    global _producer

    with _producer_lock:
        if _producer is not None:
            if _producer.bootstrap_connected():
                return _producer

            logger.warning("Kafka producer lost its bootstrap connection; reconnecting")
            _close_producer_unlocked()

        attempts = max(1, connect_attempts)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                _producer = KafkaProducer(**_producer_config())
                return _producer
            except NoBrokersAvailable as error:
                last_error = error
                logger.warning(
                    "Kafka is not ready at %s. Retry %s/%s",
                    ", ".join(configured_bootstrap_servers()),
                    attempt,
                    attempts,
                )
                if attempt < attempts:
                    time.sleep(KAFKA_CONNECT_RETRY_DELAY_SECONDS)

        raise KafkaUnavailableError(kafka_unavailable_message()) from last_error


def send_review(event: dict[str, Any]) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(1, KAFKA_SEND_ATTEMPTS + 1):
        producer = get_producer(connect_attempts=KAFKA_CONNECT_ATTEMPTS if attempt == 1 else 1)

        try:
            future = producer.send(
                settings.kafka_topic,
                key=event["product_id"],
                value=event,
            )
            metadata = future.get(timeout=KAFKA_SEND_TIMEOUT_SECONDS)

            return {
                "topic": metadata.topic,
                "partition": metadata.partition,
                "offset": metadata.offset,
            }
        except KafkaError as error:
            last_error = error
            logger.warning(
                "Kafka send failed on attempt %s/%s; resetting producer: %s",
                attempt,
                KAFKA_SEND_ATTEMPTS,
                error,
            )
            reset_producer()

    raise KafkaUnavailableError(kafka_unavailable_message()) from last_error


def probe_kafka() -> dict[str, Any]:
    try:
        producer = get_producer(connect_attempts=1)
        return {
            "status": "ok" if producer.bootstrap_connected() else "unavailable",
            "available": producer.bootstrap_connected(),
            "bootstrap_servers": configured_bootstrap_servers(),
            "topic": settings.kafka_topic,
        }
    except KafkaUnavailableError as error:
        return {
            "status": "unavailable",
            "available": False,
            "bootstrap_servers": configured_bootstrap_servers(),
            "topic": settings.kafka_topic,
            "detail": str(error),
        }


def close_producer() -> None:
    reset_producer()
