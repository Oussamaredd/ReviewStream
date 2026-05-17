import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

DEFAULT_FRONTEND_ORIGINS = ",".join(
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
)


def parse_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def default_frontend_origins() -> list[str]:
    return parse_origins(os.getenv("FRONTEND_ORIGINS", DEFAULT_FRONTEND_ORIGINS))


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "reviews")
    frontend_origins: list[str] = field(default_factory=default_frontend_origins)


settings = Settings()
