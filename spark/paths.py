import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

DEFAULT_HDFS_BASE_PATH = "hdfs://localhost:9000/reviewstream"
DEFAULT_AMAZON_REVIEWS_CSV = "data/Reviews.csv"


def hdfs_base_path() -> str:
    return os.getenv("HDFS_BASE_PATH", DEFAULT_HDFS_BASE_PATH).rstrip("/")


def hdfs_default_fs() -> str:
    configured = os.getenv("HDFS_DEFAULT_FS")
    if configured:
        return configured

    parsed = urlparse(hdfs_base_path())
    if parsed.scheme == "hdfs" and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"

    return "hdfs://namenode:9000"


def amazon_reviews_csv_path() -> str:
    return os.getenv("AMAZON_REVIEWS_CSV", DEFAULT_AMAZON_REVIEWS_CSV)


def spark_read_path(path: str) -> str:
    parsed = urlparse(path)
    if parsed.scheme:
        return path

    return Path(path).expanduser().resolve().as_uri()


def bronze_reviews_raw_path() -> str:
    return f"{hdfs_base_path()}/bronze/reviews_raw"


def bronze_amazon_reviews_raw_path() -> str:
    return f"{hdfs_base_path()}/bronze/amazon_reviews_raw"


def silver_reviews_enriched_path() -> str:
    return f"{hdfs_base_path()}/silver/reviews_enriched"


def checkpoint_path(name: str) -> str:
    return f"{hdfs_base_path()}/checkpoints/{name}"
