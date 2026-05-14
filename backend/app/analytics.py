import logging
from collections.abc import Callable
from typing import Annotated, Any, TypeVar

from fastapi import APIRouter, HTTPException, Query

from backend.app.hive_client import HiveQueryError, fetch_all, fetch_one

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)
T = TypeVar("T")

ANALYTICS_UNAVAILABLE_DETAIL = "Analytics service is unavailable"

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

ProductLimit = Annotated[int, Query(ge=1, le=100)]


def analytics_response(operation: str, query: Callable[[], T]) -> T:
    try:
        return query()
    except HiveQueryError as error:
        logger.exception("Analytics Hive query failed during %s", operation)
        raise HTTPException(status_code=503, detail=ANALYTICS_UNAVAILABLE_DETAIL) from error


def fetch_summary() -> dict[str, Any]:
    return fetch_one(SUMMARY_QUERY)


def fetch_sentiment_counts() -> list[dict[str, Any]]:
    return fetch_all(SENTIMENT_COUNTS_QUERY)


def fetch_product_scores(limit: int = 10) -> list[dict[str, Any]]:
    safe_limit = int(limit)
    return fetch_all(PRODUCT_SCORES_QUERY_TEMPLATE.format(limit=safe_limit))


@router.get("/summary")
def get_summary() -> dict[str, Any]:
    return analytics_response("summary", fetch_summary)


@router.get("/sentiment")
def get_sentiment_counts() -> list[dict[str, Any]]:
    return analytics_response("sentiment", fetch_sentiment_counts)


@router.get("/products")
def get_product_scores(limit: ProductLimit = 10) -> list[dict[str, Any]]:
    return analytics_response("products", lambda: fetch_product_scores(limit))


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
