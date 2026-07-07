import logging
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pyhive import hive
from thrift.transport import TSocket, TTransport  # type: ignore[import-untyped]

from backend.reviewstream.platform.config import Settings, settings

logger = logging.getLogger(__name__)


class HiveQueryError(RuntimeError):
    """Raised when a Hive query cannot be completed."""


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def create_hive_connection(app_settings: Settings | None = None) -> hive.Connection:
    active_settings = app_settings or settings
    if active_settings.hive_auth == "NOSASL" and active_settings.hive_socket_timeout_seconds > 0:
        socket = TSocket.TSocket(active_settings.hive_host, active_settings.hive_port)
        socket.setTimeout(int(active_settings.hive_socket_timeout_seconds * 1000))
        transport = TTransport.TBufferedTransport(socket)
        return hive.Connection(
            username=active_settings.hive_username,
            database=active_settings.hive_database,
            thrift_transport=transport,
        )

    return hive.Connection(
        host=active_settings.hive_host,
        port=active_settings.hive_port,
        username=active_settings.hive_username,
        database=active_settings.hive_database,
        auth=active_settings.hive_auth,
    )


def fetch_all(query: str, app_settings: Settings | None = None) -> list[dict[str, Any]]:
    try:
        with closing(create_hive_connection(app_settings)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(query)
                columns = [column[0].split(".")[-1] for column in cursor.description or []]
                rows = cursor.fetchall()
    except Exception as error:
        logger.debug("Hive query failed", exc_info=True)
        raise HiveQueryError("Hive query failed") from error

    return [{column: normalize_value(value) for column, value in zip(columns, row)} for row in rows]


def fetch_one(query: str, app_settings: Settings | None = None) -> dict[str, Any]:
    rows = fetch_all(query, app_settings)
    return rows[0] if rows else {}
