import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def parse_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "reviews")
    frontend_origins: list[str] = None

    def __post_init__(self):
        if self.frontend_origins is None:
            origins = os.getenv(
                "FRONTEND_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,"
                "http://localhost:5173,http://127.0.0.1:5173",
            )
            object.__setattr__(self, "frontend_origins", parse_origins(origins))


settings = Settings()
