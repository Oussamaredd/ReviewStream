from copy import deepcopy
from typing import Any

_cached_dashboard: dict[str, Any] | None = None


def get_cached_dashboard() -> dict[str, Any] | None:
    if _cached_dashboard is None:
        return None

    return deepcopy(_cached_dashboard)


def set_cached_dashboard(data: dict[str, Any]) -> None:
    global _cached_dashboard

    _cached_dashboard = deepcopy(data)


def clear_cached_dashboard() -> None:
    global _cached_dashboard

    _cached_dashboard = None
