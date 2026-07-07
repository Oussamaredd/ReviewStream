from typing import Any

from pydantic import BaseModel


class RootResponse(BaseModel):
    app: str
    status: str


class HealthResponse(BaseModel):
    status: str
    kafka_topic: str


class KafkaHealthResponse(BaseModel):
    status: str
    available: bool
    bootstrap_servers: list[str]
    topic: str
    detail: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "KafkaHealthResponse":
        return cls(
            status=str(data.get("status", "unavailable")),
            available=bool(data.get("available", False)),
            bootstrap_servers=[str(server) for server in data.get("bootstrap_servers", [])],
            topic=str(data.get("topic", "")),
            detail=str(data["detail"]) if data.get("detail") else None,
        )
