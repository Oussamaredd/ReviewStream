import logging
import os
from datetime import datetime, timezone
from threading import Lock, Thread
from time import monotonic
from typing import Any

from backend.app.analytics_cache import get_cached_dashboard, set_cached_dashboard
from backend.app.analytics_payloads import DashboardPayloadError, normalize_dashboard_payload
from backend.app.analytics_queries import fetch_dashboard
from backend.app.hive_client import HiveQueryError
from backend.app.sample_dashboard import build_sample_dashboard

logger = logging.getLogger(__name__)

CACHED_DASHBOARD_WARNING = "Hive is unavailable. Showing last successful analytics snapshot."
SAMPLE_DASHBOARD_WARNING = (
    "Hive is still warming up. Showing committed sample analytics for orientation."
)
DASHBOARD_REFRESH_INTERVAL_SECONDS = 30.0
BACKGROUND_REFRESH_ENABLED_ENV = "DASHBOARD_BACKGROUND_REFRESH_ENABLED"

_dashboard_refresh_lock = Lock()
_last_dashboard_refresh_attempt = 0.0
_dashboard_refresh_in_progress = False


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def fresh_dashboard_response(data: dict[str, Any]) -> dict[str, Any]:
    response = normalize_dashboard_payload(data)
    response.update(
        {
            "status": "fresh",
            "stale": False,
            "generated_at": utc_timestamp(),
        }
    )
    set_cached_dashboard(response)
    return response


def cached_dashboard_response(data: dict[str, Any]) -> dict[str, Any]:
    response = normalize_dashboard_payload(data)
    generated_at = data.get("generated_at")
    if generated_at:
        response["generated_at"] = generated_at
    response.update(
        {
            "status": "cached",
            "stale": True,
            "warning": CACHED_DASHBOARD_WARNING,
        }
    )
    return response


def sample_dashboard_response() -> dict[str, Any]:
    response = normalize_dashboard_payload(build_sample_dashboard())
    response.update(
        {
            "status": "sample",
            "stale": True,
            "generated_at": utc_timestamp(),
            "warning": SAMPLE_DASHBOARD_WARNING,
        }
    )
    return response


def refresh_dashboard_cache() -> None:
    global _dashboard_refresh_in_progress, _last_dashboard_refresh_attempt

    with _dashboard_refresh_lock:
        now = monotonic()
        if _dashboard_refresh_in_progress:
            return
        if now - _last_dashboard_refresh_attempt < DASHBOARD_REFRESH_INTERVAL_SECONDS:
            return
        _last_dashboard_refresh_attempt = now
        _dashboard_refresh_in_progress = True

    try:
        fresh_dashboard_response(fetch_dashboard())
    except (DashboardPayloadError, HiveQueryError):
        logger.debug("Background dashboard refresh could not update cache", exc_info=True)
    finally:
        with _dashboard_refresh_lock:
            _dashboard_refresh_in_progress = False


def background_refresh_enabled() -> bool:
    return os.getenv(BACKGROUND_REFRESH_ENABLED_ENV, "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def schedule_dashboard_refresh() -> None:
    if not background_refresh_enabled():
        return

    Thread(
        target=refresh_dashboard_cache,
        name="dashboard-cache-refresh",
        daemon=True,
    ).start()


def dashboard_response(prefer_cache: bool = True, allow_sample: bool = True) -> dict[str, Any]:
    if prefer_cache:
        cached_dashboard = get_cached_dashboard()
        if cached_dashboard is not None:
            schedule_dashboard_refresh()
            return cached_dashboard_response(cached_dashboard)

        if allow_sample:
            schedule_dashboard_refresh()
            return sample_dashboard_response()

    try:
        return fresh_dashboard_response(fetch_dashboard())
    except HiveQueryError as error:
        logger.warning("Analytics Hive query failed during dashboard: %s", error)
        cached_dashboard = get_cached_dashboard()
        if cached_dashboard is not None:
            return cached_dashboard_response(cached_dashboard)

        if allow_sample:
            return sample_dashboard_response()

        raise
