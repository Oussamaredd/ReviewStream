import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default


@dataclass(frozen=True)
class SparkSettings:
    kafka_bootstrap_servers: str = field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    )
    kafka_topic: str = field(default_factory=lambda: os.getenv("KAFKA_TOPIC", "reviews"))
    kafka_fail_on_data_loss: str = field(
        default_factory=lambda: os.getenv("SPARK_KAFKA_FAIL_ON_DATA_LOSS", "false")
    )
    shuffle_partitions: int = field(
        default_factory=lambda: env_int("SPARK_SQL_SHUFFLE_PARTITIONS", 1)
    )
    stream_trigger_seconds: int = field(
        default_factory=lambda: env_int("SPARK_STREAM_TRIGGER_SECONDS", 30)
    )
    hdfs_client_use_datanode_hostname: str = field(
        default_factory=lambda: os.getenv("HDFS_CLIENT_USE_DATANODE_HOSTNAME", "true")
    )


settings = SparkSettings()
