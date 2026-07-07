from dataclasses import dataclass
from typing import Any

from backend.reviewstream.health.application.ports import HealthSettings, KafkaProbe


@dataclass(frozen=True)
class HealthService:
    settings: HealthSettings
    kafka_probe: KafkaProbe

    def summary(self) -> dict[str, str]:
        return {
            "status": "ok",
            "kafka_topic": self.settings.kafka_topic,
        }

    def kafka(self) -> dict[str, Any]:
        return self.kafka_probe.probe()
