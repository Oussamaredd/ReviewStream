import logging
from collections.abc import Callable
from typing import Annotated, Any, TypeVar

from fastapi import APIRouter, HTTPException, Query

from backend.app.hive_client import HiveQueryError, fetch_all, fetch_one

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)
T = TypeVar("T")

ANALYTICS_UNAVAILABLE_DETAIL = "Analytics service is unavailable"

Limit = Annotated[int, Query(ge=1, le=100)]
RecentLimit = Annotated[int, Query(ge=1, le=100)]
MinReviews = Annotated[int, Query(ge=1, le=1_000_000)]

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
        CAST('' AS STRING) AS text,
        source,
        review_id,
        created_at,
        text_length,
        word_count,
        has_negative_keywords,
        has_positive_keywords
    FROM reviews_enriched
    WHERE source = 'web'
        AND created_at IS NOT NULL
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


def analytics_response(operation: str, query: Callable[[], T]) -> T:
    try:
        return query()
    except HiveQueryError as error:
        logger.exception("Analytics Hive query failed during %s", operation)
        raise HTTPException(status_code=503, detail=ANALYTICS_UNAVAILABLE_DETAIL) from error


def bounded_int(value: int) -> int:
    return int(value)


def fetch_summary() -> dict[str, Any]:
    return fetch_one(SUMMARY_QUERY)


def fetch_sentiment_counts() -> list[dict[str, Any]]:
    return fetch_all(SENTIMENT_COUNTS_QUERY)


def fetch_score_distribution() -> list[dict[str, Any]]:
    return fetch_all(SCORE_DISTRIBUTION_QUERY)


def fetch_product_scores(limit: int = 10) -> list[dict[str, Any]]:
    return fetch_all(PRODUCT_SCORES_QUERY_TEMPLATE.format(limit=bounded_int(limit)))


def fetch_top_products(limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
    return fetch_all(
        RANKED_PRODUCTS_QUERY_TEMPLATE.format(
            direction="DESC",
            limit=bounded_int(limit),
            min_reviews=bounded_int(min_reviews),
        )
    )


def fetch_worst_products(limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
    return fetch_all(
        RANKED_PRODUCTS_QUERY_TEMPLATE.format(
            direction="ASC",
            limit=bounded_int(limit),
            min_reviews=bounded_int(min_reviews),
        )
    )


def fetch_recent_reviews(limit: int = 20) -> list[dict[str, Any]]:
    return fetch_all(RECENT_REVIEWS_QUERY_TEMPLATE.format(limit=bounded_int(limit)))


def fetch_negative_products(limit: int = 10, min_reviews: int = 3) -> list[dict[str, Any]]:
    return fetch_all(
        NEGATIVE_PRODUCTS_QUERY_TEMPLATE.format(
            limit=bounded_int(limit),
            min_reviews=bounded_int(min_reviews),
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
        "top_products": fetch_top_products(limit=10, min_reviews=5),
        "worst_products": fetch_worst_products(limit=10, min_reviews=5),
        "negative_products": fetch_negative_products(limit=10, min_reviews=3),
        "recent_reviews": fetch_recent_reviews(limit=20),
        "sources": fetch_sources(),
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
def get_dashboard() -> dict[str, Any]:
    return analytics_response("dashboard", fetch_dashboard)


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
