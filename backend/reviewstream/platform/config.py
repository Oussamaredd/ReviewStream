import os
from dataclasses import dataclass, field
from typing import Mapping

from dotenv import load_dotenv

DEFAULT_FRONTEND_ORIGINS = ",".join(
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
)


class ConfigError(ValueError):
    """Raised when environment configuration is invalid."""


def parse_non_empty(value: str, name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ConfigError(f"{name} cannot be empty")
    return stripped


def parse_kafka_bootstrap_servers(value: str) -> str:
    servers = [server.strip() for server in value.split(",") if server.strip()]
    if not servers:
        raise ConfigError("KAFKA_BOOTSTRAP_SERVERS must contain at least one server")
    return ",".join(servers)


def parse_origins(value: str) -> list[str]:
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return validate_origins(origins)


def validate_origins(origins: list[str]) -> list[str]:
    origins = [origin.strip() for origin in origins if origin.strip()]
    if "*" in origins:
        raise ConfigError("FRONTEND_ORIGINS cannot contain '*' while credentials are enabled")
    return origins


def parse_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ConfigError(f"{name} must be an integer") from error


def parse_float(value: str, name: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise ConfigError(f"{name} must be a number") from error


def env_value(env: Mapping[str, str], name: str, default: str) -> str:
    return env.get(name, default)


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap_servers: str = "127.0.0.1:9092"
    kafka_topic: str = "reviews"
    frontend_origins: list[str] = field(
        default_factory=lambda: parse_origins(DEFAULT_FRONTEND_ORIGINS)
    )
    hive_host: str = "localhost"
    hive_port: int = 10000
    hive_database: str = "reviewstream"
    hive_username: str = "root"
    hive_auth: str = "NOSASL"
    hive_socket_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "kafka_bootstrap_servers",
            parse_kafka_bootstrap_servers(self.kafka_bootstrap_servers),
        )
        object.__setattr__(
            self,
            "kafka_topic",
            parse_non_empty(self.kafka_topic, "KAFKA_TOPIC"),
        )
        object.__setattr__(self, "frontend_origins", validate_origins(self.frontend_origins))
        object.__setattr__(self, "hive_host", parse_non_empty(self.hive_host, "HIVE_HOST"))
        object.__setattr__(
            self,
            "hive_database",
            parse_non_empty(self.hive_database, "HIVE_DATABASE"),
        )
        object.__setattr__(
            self,
            "hive_username",
            parse_non_empty(self.hive_username, "HIVE_USERNAME"),
        )
        object.__setattr__(self, "hive_auth", parse_non_empty(self.hive_auth, "HIVE_AUTH"))
        if self.hive_socket_timeout_seconds < 0:
            raise ConfigError("HIVE_SOCKET_TIMEOUT_SECONDS cannot be negative")

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        load_env_file: bool = True,
    ) -> "Settings":
        if load_env_file:
            load_dotenv()

        if env is None:
            env = os.environ

        return cls(
            kafka_bootstrap_servers=env_value(env, "KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"),
            kafka_topic=env_value(env, "KAFKA_TOPIC", "reviews"),
            frontend_origins=parse_origins(
                env_value(env, "FRONTEND_ORIGINS", DEFAULT_FRONTEND_ORIGINS)
            ),
            hive_host=env_value(env, "HIVE_HOST", "localhost"),
            hive_port=parse_int(env_value(env, "HIVE_PORT", "10000"), "HIVE_PORT"),
            hive_database=env_value(env, "HIVE_DATABASE", "reviewstream"),
            hive_username=env_value(env, "HIVE_USERNAME", "root"),
            hive_auth=env_value(env, "HIVE_AUTH", "NOSASL"),
            hive_socket_timeout_seconds=parse_float(
                env_value(env, "HIVE_SOCKET_TIMEOUT_SECONDS", "30"),
                "HIVE_SOCKET_TIMEOUT_SECONDS",
            ),
        )


settings = Settings.from_env()
