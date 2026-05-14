import logging
import os
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv
from pyhive import hive

load_dotenv()

HIVE_HOST = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT = int(os.getenv("HIVE_PORT", "10000"))
HIVE_DATABASE = os.getenv("HIVE_DATABASE", "reviewstream")
HIVE_USERNAME = os.getenv("HIVE_USERNAME", "root")
HIVE_AUTH = os.getenv("HIVE_AUTH", "NOSASL")

logger = logging.getLogger(__name__)


class HiveQueryError(RuntimeError):
    """Raised when a Hive query cannot be completed."""


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def fetch_all(query: str) -> list[dict[str, Any]]:
    try:
        with closing(
            hive.Connection(
                host=HIVE_HOST,
                port=HIVE_PORT,
                username=HIVE_USERNAME,
                database=HIVE_DATABASE,
                auth=HIVE_AUTH,
            )
        ) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(query)
                columns = [column[0].split(".")[-1] for column in cursor.description or []]
                rows = cursor.fetchall()
    except Exception as error:
        logger.exception("Hive query failed")
        raise HiveQueryError("Hive query failed") from error

    return [{column: normalize_value(value) for column, value in zip(columns, row)} for row in rows]


def fetch_one(query: str) -> dict[str, Any]:
    rows = fetch_all(query)
    return rows[0] if rows else {}
