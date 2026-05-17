from typing import Any


class DashboardPayloadError(ValueError):
    """Raised when the dashboard payload is incomplete or unsafe to cache."""


DASHBOARD_LIST_KEYS = [
    "sentiment",
    "score_distribution",
    "top_products",
    "worst_products",
    "negative_products",
    "recent_reviews",
    "sources",
    "opinions",
]

DASHBOARD_DICT_KEYS = [
    "summary",
    "negative_keywords",
    "positive_keywords",
]


def as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        summary = {}

    return {
        "total_reviews": as_int(summary.get("total_reviews")),
        "average_score": as_float(summary.get("average_score")),
        "first_review_at": summary.get("first_review_at"),
        "last_review_at": summary.get("last_review_at"),
    }


def normalize_keyword_counts(data: dict[str, Any] | None, keyword_type: str) -> dict[str, Any]:
    if data is None:
        data = {}

    return {
        "keyword_type": data.get("keyword_type") or keyword_type,
        "matching_reviews": as_int(data.get("matching_reviews")),
    }


def validate_dashboard_payload(data: dict[str, Any]) -> None:
    required_keys = {"summary", *DASHBOARD_LIST_KEYS, *DASHBOARD_DICT_KEYS}
    missing_keys = sorted(required_keys.difference(data))
    if missing_keys:
        raise DashboardPayloadError(
            f"Dashboard payload is missing required keys: {', '.join(missing_keys)}"
        )

    if not isinstance(data["summary"], dict):
        raise DashboardPayloadError("Dashboard summary must be an object")

    for key in DASHBOARD_LIST_KEYS:
        if not isinstance(data[key], list):
            raise DashboardPayloadError(f"Dashboard {key} must be a list")

    for key in DASHBOARD_DICT_KEYS:
        if not isinstance(data[key], dict):
            raise DashboardPayloadError(f"Dashboard {key} must be an object")


def is_test_product_row(row: dict[str, Any]) -> bool:
    return str(row.get("product_id") or "").upper().startswith("E2E")


def has_opinion_text(row: dict[str, Any]) -> bool:
    return bool(str(row.get("text") or "").strip())


def filter_product_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not is_test_product_row(row)]


def filter_opinion_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not is_test_product_row(row) and has_opinion_text(row)]


def normalize_dashboard_payload(data: dict[str, Any]) -> dict[str, Any]:
    validate_dashboard_payload(data)

    return {
        "summary": normalize_summary(data["summary"]),
        "sentiment": data["sentiment"],
        "score_distribution": data["score_distribution"],
        "top_products": filter_product_rows(data["top_products"]),
        "worst_products": filter_product_rows(data["worst_products"]),
        "negative_products": filter_product_rows(data["negative_products"]),
        "recent_reviews": filter_opinion_rows(data["recent_reviews"]),
        "sources": data["sources"],
        "opinions": filter_opinion_rows(data["opinions"]),
        "negative_keywords": normalize_keyword_counts(data["negative_keywords"], "negative"),
        "positive_keywords": normalize_keyword_counts(data["positive_keywords"], "positive"),
    }
