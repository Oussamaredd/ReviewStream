from copy import deepcopy
from threading import Lock
from typing import Any


class InMemoryDashboardCache:
    def __init__(self) -> None:
        self._cached_dashboard: dict[str, Any] | None = None
        self._lock = Lock()

    def get(self) -> dict[str, Any] | None:
        with self._lock:
            if self._cached_dashboard is None:
                return None

            return deepcopy(self._cached_dashboard)

    def set(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._cached_dashboard = deepcopy(data)

    def clear(self) -> None:
        with self._lock:
            self._cached_dashboard = None
