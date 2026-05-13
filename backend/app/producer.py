import json
import time
from typing import Any

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from .config import settings

_producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    global _producer

    if _producer is not None:
        return _producer

    for attempt in range(1, 11):
        try:
            _producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda key: key.encode("utf-8") if key else None,
                acks="all",
                retries=3,
            )
            return _producer

        except NoBrokersAvailable:
            print(f"Kafka not ready yet. Retry {attempt}/10...")
            time.sleep(2)

    raise RuntimeError("Could not connect to Kafka broker.")


def send_review(event: dict[str, Any]) -> dict[str, Any]:
    producer = get_producer()

    future = producer.send(
        settings.kafka_topic,
        key=event["product_id"],
        value=event,
    )

    metadata = future.get(timeout=10)

    return {
        "topic": metadata.topic,
        "partition": metadata.partition,
        "offset": metadata.offset,
    }


def close_producer() -> None:
    global _producer

    if _producer is not None:
        _producer.flush(timeout=10)
        _producer.close(timeout=10)
        _producer = None
