import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock, Thread
from time import monotonic
from typing import Any

from backend.reviewstream.analytics.application.dashboard_payloads import (
    DashboardPayloadError,
    normalize_dashboard_payload,
)
from backend.reviewstream.analytics.application.errors import AnalyticsUnavailableError
from backend.reviewstream.analytics.application.ports import DashboardCache, SampleDashboardProvider
from backend.reviewstream.analytics.application.queries import AnalyticsQueryService

logger = logging.getLogger(__name__)

CACHED_DASHBOARD_WARNING = "Hive is unavailable. Showing last successful analytics snapshot."
SAMPLE_DASHBOARD_WARNING = (
    "Hive is still warming up. Showing committed sample analytics for orientation."
)
DASHBOARD_REFRESH_INTERVAL_SECONDS = 30.0
BACKGROUND_REFRESH_ENABLED_ENV = "DASHBOARD_BACKGROUND_REFRESH_ENABLED"


@dataclass
class DashboardService:
    analytics_service: AnalyticsQueryService
    cache: DashboardCache
    sample_dashboard_provider: SampleDashboardProvider
    refresh_interval_seconds: float = DASHBOARD_REFRESH_INTERVAL_SECONDS
    background_refresh_enabled_env: str = BACKGROUND_REFRESH_ENABLED_ENV
    _dashboard_refresh_lock: Lock = field(default_factory=Lock, init=False)
    _last_dashboard_refresh_attempt: float = field(default=0.0, init=False)
    _dashboard_refresh_in_progress: bool = field(default=False, init=False)

    def utc_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def fetch_dashboard(self) -> dict[str, Any]:
        return self.analytics_service.fetch_dashboard()

    def fresh_dashboard_response(self, data: dict[str, Any]) -> dict[str, Any]:
        response = normalize_dashboard_payload(data)
        response.update(
            {
                "status": "fresh",
                "stale": False,
                "generated_at": self.utc_timestamp(),
            }
        )
        self.cache.set(response)
        return response

    def cached_dashboard_response(self, data: dict[str, Any]) -> dict[str, Any]:
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

    def sample_dashboard_response(self) -> dict[str, Any]:
        response = normalize_dashboard_payload(self.sample_dashboard_provider.build_dashboard())
        response.update(
            {
                "status": "sample",
                "stale": True,
                "generated_at": self.utc_timestamp(),
                "warning": SAMPLE_DASHBOARD_WARNING,
            }
        )
        return response

    def refresh_dashboard_cache(self) -> None:
        with self._dashboard_refresh_lock:
            now = monotonic()
            if self._dashboard_refresh_in_progress:
                return
            if now - self._last_dashboard_refresh_attempt < self.refresh_interval_seconds:
                return
            self._last_dashboard_refresh_attempt = now
            self._dashboard_refresh_in_progress = True

        try:
            self.fresh_dashboard_response(self.fetch_dashboard())
        except (DashboardPayloadError, AnalyticsUnavailableError):
            logger.debug("Background dashboard refresh could not update cache", exc_info=True)
        finally:
            with self._dashboard_refresh_lock:
                self._dashboard_refresh_in_progress = False

    def reserve_dashboard_refresh(self) -> bool:
        with self._dashboard_refresh_lock:
            now = monotonic()
            if self._dashboard_refresh_in_progress:
                return False
            if now - self._last_dashboard_refresh_attempt < self.refresh_interval_seconds:
                return False

            self._last_dashboard_refresh_attempt = now
            self._dashboard_refresh_in_progress = True
            return True

    def run_reserved_dashboard_refresh(self) -> None:
        try:
            self.fresh_dashboard_response(self.fetch_dashboard())
        except (DashboardPayloadError, AnalyticsUnavailableError):
            logger.debug("Background dashboard refresh could not update cache", exc_info=True)
        finally:
            with self._dashboard_refresh_lock:
                self._dashboard_refresh_in_progress = False

    def background_refresh_enabled(self) -> bool:
        return os.getenv(self.background_refresh_enabled_env, "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def schedule_dashboard_refresh(self) -> None:
        if not self.background_refresh_enabled():
            return
        if not self.reserve_dashboard_refresh():
            return

        Thread(
            target=self.run_reserved_dashboard_refresh,
            name="dashboard-cache-refresh",
            daemon=True,
        ).start()

    def dashboard_response(
        self, prefer_cache: bool = True, allow_sample: bool = True
    ) -> dict[str, Any]:
        if prefer_cache:
            cached_dashboard = self.cache.get()
            if cached_dashboard is not None:
                self.schedule_dashboard_refresh()
                return self.cached_dashboard_response(cached_dashboard)

        try:
            return self.fresh_dashboard_response(self.fetch_dashboard())
        except AnalyticsUnavailableError as error:
            logger.warning("Analytics Hive query failed during dashboard: %s", error)
            cached_dashboard = self.cache.get()
            if cached_dashboard is not None:
                return self.cached_dashboard_response(cached_dashboard)

            if allow_sample:
                return self.sample_dashboard_response()

            raise
