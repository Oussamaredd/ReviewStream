import logging
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from typing import Annotated, Any, Literal, TypeVar

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from backend.app.analytics_cache import get_cached_dashboard, set_cached_dashboard
from backend.app.catalog import enrich_product_rows
from backend.app.hive_client import HiveQueryError, fetch_all, fetch_one
from backend.app.sample_dashboard import build_sample_dashboard

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)
T = TypeVar("T")

ANALYTICS_UNAVAILABLE_DETAIL = "Analytics service is unavailable"

Limit = Annotated[int, Query(ge=1, le=100)]
RecentLimit = Annotated[int, Query(ge=1, le=100)]
MinReviews = Annotated[int, Query(ge=1, le=1_000_000)]
SentimentFilter = Literal["positive", "neutral", "negative"]

CACHED_DASHBOARD_WARNING = "Hive is unavailable. Showing last successful analytics snapshot."
SAMPLE_DASHBOARD_WARNING = (
    "Hive is still warming up. Showing committed sample analytics for orientation."
)
DASHBOARD_REFRESH_INTERVAL_SECONDS = 30.0
_dashboard_refresh_lock = Lock()
_last_dashboard_refresh_attempt = 0.0
_dashboard_refresh_in_progress = False

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

SUMMARY_QUERY = """
    SELECT
        COUNT(*) AS total_reviews,
        AVG(score) AS average_score,
        MIN(created_at) AS first_review_at,
        MAX(created_at) AS last_review_at
    FROM reviews_enriched
    """

SENTIMENT_COUNTS_QUERY = """
    SELECT
        sentiment,
        COUNT(*) AS review_count
    FROM reviews_enriched
    GROUP BY sentiment
    ORDER BY sentiment
    """

SCORE_DISTRIBUTION_QUERY = """
    SELECT
        score,
        COUNT(*) AS review_count
    FROM reviews_enriched
    GROUP BY score
    ORDER BY score
    """

PRODUCT_SCORES_QUERY_TEMPLATE = """
    SELECT
        product_id,
        COUNT(*) AS review_count,
        AVG(score) AS average_score
    FROM reviews_enriched
    GROUP BY product_id
    ORDER BY review_count DESC, average_score DESC
    LIMIT {limit}
    """

RANKED_PRODUCTS_QUERY_TEMPLATE = """
    SELECT
        product_id,
        COUNT(*) AS review_count,
        AVG(score) AS average_score
    FROM reviews_enriched
    GROUP BY product_id
    HAVING COUNT(*) >= {min_reviews}
    ORDER BY average_score {direction}, review_count DESC
    LIMIT {limit}
    """

RECENT_REVIEWS_QUERY_TEMPLATE = """
    SELECT
        product_id,
        user_id,
        score,
        sentiment,
        text,
        source,
        review_id,
        created_at,
        text_length,
        word_count,
        has_negative_keywords,
        has_positive_keywords
    FROM reviews_enriched
    WHERE created_at IS NOT NULL
    ORDER BY created_at DESC
    LIMIT {limit}
    """

OPINIONS_QUERY_TEMPLATE = """
    SELECT
        product_id,
        user_id,
        score,
        sentiment,
        text,
        source,
        review_id,
        created_at,
        text_length,
        word_count,
        has_negative_keywords,
        has_positive_keywords
    FROM reviews_enriched
    {where_clause}
    ORDER BY created_at DESC
    LIMIT {limit}
    """

NEGATIVE_PRODUCTS_QUERY_TEMPLATE = """
    SELECT
        product_id,
        SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_review_count,
        COUNT(*) AS review_count,
        AVG(score) AS average_score
    FROM reviews_enriched
    GROUP BY product_id
    HAVING COUNT(*) >= {min_reviews}
        AND SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) > 0
    ORDER BY negative_review_count DESC, average_score ASC
    LIMIT {limit}
    """

SOURCES_QUERY = """
    SELECT
        COALESCE(source, 'unknown') AS source,
        COUNT(*) AS review_count
    FROM reviews_enriched
    GROUP BY COALESCE(source, 'unknown')
    ORDER BY review_count DESC, source
    """

NEGATIVE_KEYWORD_COUNT_QUERY = """
    SELECT
        COUNT(*) AS matching_reviews
    FROM reviews_enriched
    WHERE has_negative_keywords = true
    """

POSITIVE_KEYWORD_COUNT_QUERY = """
    SELECT
        COUNT(*) AS matching_reviews
    FROM reviews_enriched
    WHERE has_positive_keywords = true
    """


class DashboardPayloadError(ValueError):
    """Raised when the dashboard payload is incomplete or unsafe to cache."""


def analytics_response(operation: str, query: Callable[[], T]) -> T:
    try:
        return query()
    except HiveQueryError as error:
        logger.exception("Analytics Hive query failed during %s", operation)
        raise HTTPException(status_code=503, detail=ANALYTICS_UNAVAILABLE_DETAIL) from error


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def bounded_int(value: int) -> int:
    return int(value)


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


def normalize_dashboard_payload(data: dict[str, Any]) -> dict[str, Any]:
    validate_dashboard_payload(data)

    return {
        "summary": normalize_summary(data["summary"]),
        "sentiment": data["sentiment"],
        "score_distribution": data["score_distribution"],
        "top_products": data["top_products"],
        "worst_products": data["worst_products"],
        "negative_products": data["negative_products"],
        "recent_reviews": data["recent_reviews"],
        "sources": data["sources"],
        "opinions": data["opinions"],
        "negative_keywords": normalize_keyword_counts(data["negative_keywords"], "negative"),
        "positive_keywords": normalize_keyword_counts(data["positive_keywords"], "positive"),
    }


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
    response = dict(data)
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


def fetch_summary() -> dict[str, Any]:
    return normalize_summary(fetch_one(SUMMARY_QUERY))


def fetch_sentiment_counts() -> list[dict[str, Any]]:
    return fetch_all(SENTIMENT_COUNTS_QUERY)


def fetch_score_distribution() -> list[dict[str, Any]]:
    return fetch_all(SCORE_DISTRIBUTION_QUERY)


def fetch_product_scores(limit: int = 10) -> list[dict[str, Any]]:
    return enrich_product_rows(
        fetch_all(PRODUCT_SCORES_QUERY_TEMPLATE.format(limit=bounded_int(limit)))
    )


def fetch_top_products(limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
    return enrich_product_rows(
        fetch_all(
            RANKED_PRODUCTS_QUERY_TEMPLATE.format(
                direction="DESC",
                limit=bounded_int(limit),
                min_reviews=bounded_int(min_reviews),
            )
        )
    )


def fetch_worst_products(limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
    return enrich_product_rows(
        fetch_all(
            RANKED_PRODUCTS_QUERY_TEMPLATE.format(
                direction="ASC",
                limit=bounded_int(limit),
                min_reviews=bounded_int(min_reviews),
            )
        )
    )


def fetch_recent_reviews(limit: int = 20) -> list[dict[str, Any]]:
    return enrich_product_rows(
        fetch_all(RECENT_REVIEWS_QUERY_TEMPLATE.format(limit=bounded_int(limit)))
    )


def fetch_opinions(
    limit: int = 50, sentiment: SentimentFilter | None = None
) -> list[dict[str, Any]]:
    where_clauses = ["created_at IS NOT NULL"]
    if sentiment is not None:
        where_clauses.append(f"sentiment = '{sentiment}'")

    query = OPINIONS_QUERY_TEMPLATE.format(
        where_clause=f"WHERE {' AND '.join(where_clauses)}",
        limit=bounded_int(limit),
    )
    return enrich_product_rows(fetch_all(query))


def fetch_negative_products(limit: int = 10, min_reviews: int = 3) -> list[dict[str, Any]]:
    return enrich_product_rows(
        fetch_all(
            NEGATIVE_PRODUCTS_QUERY_TEMPLATE.format(
                limit=bounded_int(limit),
                min_reviews=bounded_int(min_reviews),
            )
        )
    )


def fetch_sources() -> list[dict[str, Any]]:
    return fetch_all(SOURCES_QUERY)


def fetch_negative_keyword_counts() -> dict[str, Any]:
    result = fetch_one(NEGATIVE_KEYWORD_COUNT_QUERY)
    return {
        "keyword_type": "negative",
        "matching_reviews": result.get("matching_reviews", 0),
    }


def fetch_positive_keyword_counts() -> dict[str, Any]:
    result = fetch_one(POSITIVE_KEYWORD_COUNT_QUERY)
    return {
        "keyword_type": "positive",
        "matching_reviews": result.get("matching_reviews", 0),
    }


def fetch_dashboard() -> dict[str, Any]:
    return {
        "summary": fetch_summary(),
        "sentiment": fetch_sentiment_counts(),
        "score_distribution": fetch_score_distribution(),
        "top_products": fetch_top_products(limit=10, min_reviews=1),
        "worst_products": fetch_worst_products(limit=10, min_reviews=1),
        "negative_products": fetch_negative_products(limit=10, min_reviews=1),
        "recent_reviews": fetch_recent_reviews(limit=20),
        "sources": fetch_sources(),
        "opinions": fetch_opinions(limit=20),
        "negative_keywords": fetch_negative_keyword_counts(),
        "positive_keywords": fetch_positive_keyword_counts(),
    }


@router.get("/summary")
def get_summary() -> dict[str, Any]:
    return analytics_response("summary", fetch_summary)


@router.get("/sentiment")
def get_sentiment_counts() -> list[dict[str, Any]]:
    return analytics_response("sentiment", fetch_sentiment_counts)


@router.get("/products")
def get_product_scores(limit: Limit = 10) -> list[dict[str, Any]]:
    return analytics_response("products", lambda: fetch_product_scores(limit))


@router.get("/score-distribution")
def get_score_distribution() -> list[dict[str, Any]]:
    return analytics_response("score_distribution", fetch_score_distribution)


@router.get("/top-products")
def get_top_products(limit: Limit = 10, min_reviews: MinReviews = 5) -> list[dict[str, Any]]:
    return analytics_response(
        "top_products",
        lambda: fetch_top_products(limit=limit, min_reviews=min_reviews),
    )


@router.get("/worst-products")
def get_worst_products(limit: Limit = 10, min_reviews: MinReviews = 5) -> list[dict[str, Any]]:
    return analytics_response(
        "worst_products",
        lambda: fetch_worst_products(limit=limit, min_reviews=min_reviews),
    )


@router.get("/recent")
def get_recent_reviews(limit: RecentLimit = 20) -> list[dict[str, Any]]:
    return analytics_response("recent_reviews", lambda: fetch_recent_reviews(limit))


@router.get("/opinions")
def get_opinions(
    limit: Limit = 50,
    sentiment: Annotated[SentimentFilter | None, Query()] = None,
) -> list[dict[str, Any]]:
    return analytics_response("opinions", lambda: fetch_opinions(limit=limit, sentiment=sentiment))


@router.get("/negative-products")
def get_negative_products(limit: Limit = 10, min_reviews: MinReviews = 3) -> list[dict[str, Any]]:
    return analytics_response(
        "negative_products",
        lambda: fetch_negative_products(limit=limit, min_reviews=min_reviews),
    )


@router.get("/sources")
def get_sources() -> list[dict[str, Any]]:
    return analytics_response("sources", fetch_sources)


@router.get("/keywords/negative")
def get_negative_keyword_counts() -> dict[str, Any]:
    return analytics_response("negative_keywords", fetch_negative_keyword_counts)


@router.get("/keywords/positive")
def get_positive_keyword_counts() -> dict[str, Any]:
    return analytics_response("positive_keywords", fetch_positive_keyword_counts)


@router.get("/dashboard")
def get_dashboard(
    background_tasks: BackgroundTasks,
    prefer_cache: bool = True,
    allow_sample: bool = True,
) -> dict[str, Any]:
    if prefer_cache:
        cached_dashboard = get_cached_dashboard()
        if cached_dashboard is not None:
            background_tasks.add_task(refresh_dashboard_cache)
            return cached_dashboard_response(cached_dashboard)

        if allow_sample:
            background_tasks.add_task(refresh_dashboard_cache)
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

        raise HTTPException(status_code=503, detail=ANALYTICS_UNAVAILABLE_DETAIL) from error
    except DashboardPayloadError as error:
        logger.exception("Analytics dashboard payload was not safe to cache")
        raise HTTPException(status_code=503, detail=ANALYTICS_UNAVAILABLE_DETAIL) from error


@router.get("")
@router.get("/")
def get_analytics() -> dict[str, Any]:
    return analytics_response(
        "aggregate",
        lambda: {
            "summary": fetch_summary(),
            "sentiment": fetch_sentiment_counts(),
            "products": fetch_product_scores(limit=10),
        },
    )
