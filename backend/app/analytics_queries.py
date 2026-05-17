from typing import Any, Literal

from backend.app.analytics_payloads import normalize_summary
from backend.app.analytics_sql import (
    ANALYTICS_ROW_FILTER,
    NEGATIVE_KEYWORD_COUNT_QUERY,
    NEGATIVE_PRODUCTS_QUERY_TEMPLATE,
    OPINION_TEXT_FILTER,
    OPINIONS_QUERY_TEMPLATE,
    POSITIVE_KEYWORD_COUNT_QUERY,
    PRODUCT_SCORES_QUERY_TEMPLATE,
    RANKED_PRODUCTS_QUERY_TEMPLATE,
    RECENT_REVIEWS_QUERY_TEMPLATE,
    SCORE_DISTRIBUTION_QUERY,
    SENTIMENT_COUNTS_QUERY,
    SOURCES_QUERY,
    SUMMARY_QUERY,
)
from backend.app.catalog import enrich_product_rows
from backend.app.hive_client import fetch_all, fetch_one

SentimentFilter = Literal["positive", "neutral", "negative"]


def bounded_int(value: int) -> int:
    return int(value)


def fetch_summary() -> dict[str, Any]:
    return normalize_summary(fetch_one(SUMMARY_QUERY))


def fetch_sentiment_counts() -> list[dict[str, Any]]:
    return fetch_all(SENTIMENT_COUNTS_QUERY)


def fetch_score_distribution() -> list[dict[str, Any]]:
    return fetch_all(SCORE_DISTRIBUTION_QUERY)


def fetch_product_scores(limit: int = 10) -> list[dict[str, Any]]:
    return enrich_product_rows(
        fetch_all(
            PRODUCT_SCORES_QUERY_TEMPLATE.format(
                limit=bounded_int(limit),
                row_filter=ANALYTICS_ROW_FILTER,
            )
        )
    )


def fetch_top_products(limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
    return enrich_product_rows(
        fetch_all(
            RANKED_PRODUCTS_QUERY_TEMPLATE.format(
                direction="DESC",
                limit=bounded_int(limit),
                min_reviews=bounded_int(min_reviews),
                row_filter=ANALYTICS_ROW_FILTER,
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
                row_filter=ANALYTICS_ROW_FILTER,
            )
        )
    )


def fetch_recent_reviews(limit: int = 20) -> list[dict[str, Any]]:
    return enrich_product_rows(
        fetch_all(
            RECENT_REVIEWS_QUERY_TEMPLATE.format(
                limit=bounded_int(limit),
                row_filter=ANALYTICS_ROW_FILTER,
                text_filter=OPINION_TEXT_FILTER,
            )
        )
    )


def fetch_opinions(
    limit: int = 50, sentiment: SentimentFilter | None = None
) -> list[dict[str, Any]]:
    where_clauses = [
        "created_at IS NOT NULL",
        ANALYTICS_ROW_FILTER,
        OPINION_TEXT_FILTER,
    ]
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
                row_filter=ANALYTICS_ROW_FILTER,
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
