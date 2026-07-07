from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from backend.reviewstream.analytics.application.dashboard_payloads import normalize_summary
from backend.reviewstream.analytics.application.errors import AnalyticsUnavailableError
from backend.reviewstream.analytics.application.types import SentimentFilter
from backend.reviewstream.analytics.infrastructure.hive_sql import (
    ANALYTICS_ROW_FILTER,
    NEGATIVE_KEYWORD_COUNT_QUERY,
    NEGATIVE_PRODUCTS_QUERY_TEMPLATE,
    OPINION_TEXT_FILTER,
    OPINIONS_QUERY_TEMPLATE,
    POSITIVE_KEYWORD_COUNT_QUERY,
    PRODUCT_SCORES_QUERY_TEMPLATE,
    RECENT_REVIEWS_QUERY_TEMPLATE,
    SCORE_DISTRIBUTION_QUERY,
    SENTIMENT_COUNTS_QUERY,
    SOURCES_QUERY,
    SUMMARY_QUERY,
    TOP_PRODUCTS_QUERY_TEMPLATE,
    WORST_PRODUCTS_QUERY_TEMPLATE,
)
from backend.reviewstream.platform.config import Settings
from backend.reviewstream.platform.hive_client import HiveQueryError, fetch_all, fetch_one

ProductRowEnricher = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


def bounded_int(value: int) -> int:
    return int(value)


@dataclass(frozen=True)
class HiveAnalyticsRepository:
    enrich_product_rows: ProductRowEnricher
    app_settings: Settings | None = None

    def _fetch_all(self, query: str) -> list[dict[str, Any]]:
        try:
            return fetch_all(query, self.app_settings)
        except (HiveQueryError, KeyError, TypeError, ValueError) as error:
            raise AnalyticsUnavailableError("Analytics service is unavailable") from error

    def _fetch_one(self, query: str) -> dict[str, Any]:
        try:
            return fetch_one(query, self.app_settings)
        except (HiveQueryError, KeyError, TypeError, ValueError) as error:
            raise AnalyticsUnavailableError("Analytics service is unavailable") from error

    def fetch_summary(self) -> dict[str, Any]:
        return normalize_summary(self._fetch_one(SUMMARY_QUERY))

    def fetch_sentiment_counts(self) -> list[dict[str, Any]]:
        return self._fetch_all(SENTIMENT_COUNTS_QUERY)

    def fetch_score_distribution(self) -> list[dict[str, Any]]:
        return self._fetch_all(SCORE_DISTRIBUTION_QUERY)

    def fetch_product_scores(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.enrich_product_rows(
            self._fetch_all(
                PRODUCT_SCORES_QUERY_TEMPLATE.format(
                    limit=bounded_int(limit),
                    row_filter=ANALYTICS_ROW_FILTER,
                )
            )
        )

    def fetch_top_products(self, limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
        return self.enrich_product_rows(
            self._fetch_all(
                TOP_PRODUCTS_QUERY_TEMPLATE.format(
                    limit=bounded_int(limit),
                    min_reviews=bounded_int(min_reviews),
                    row_filter=ANALYTICS_ROW_FILTER,
                )
            )
        )

    def fetch_worst_products(self, limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
        return self.enrich_product_rows(
            self._fetch_all(
                WORST_PRODUCTS_QUERY_TEMPLATE.format(
                    limit=bounded_int(limit),
                    min_reviews=bounded_int(min_reviews),
                    row_filter=ANALYTICS_ROW_FILTER,
                )
            )
        )

    def fetch_recent_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.enrich_product_rows(
            self._fetch_all(
                RECENT_REVIEWS_QUERY_TEMPLATE.format(
                    limit=bounded_int(limit),
                    row_filter=ANALYTICS_ROW_FILTER,
                    text_filter=OPINION_TEXT_FILTER,
                )
            )
        )

    def fetch_opinions(
        self, limit: int = 50, sentiment: SentimentFilter | None = None
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
        return self.enrich_product_rows(self._fetch_all(query))

    def fetch_negative_products(
        self, limit: int = 10, min_reviews: int = 3
    ) -> list[dict[str, Any]]:
        return self.enrich_product_rows(
            self._fetch_all(
                NEGATIVE_PRODUCTS_QUERY_TEMPLATE.format(
                    limit=bounded_int(limit),
                    min_reviews=bounded_int(min_reviews),
                    row_filter=ANALYTICS_ROW_FILTER,
                )
            )
        )

    def fetch_sources(self) -> list[dict[str, Any]]:
        return self._fetch_all(SOURCES_QUERY)

    def fetch_negative_keyword_counts(self) -> dict[str, Any]:
        result = self._fetch_one(NEGATIVE_KEYWORD_COUNT_QUERY)
        return {
            "keyword_type": "negative",
            "matching_reviews": result.get("matching_reviews", 0),
        }

    def fetch_positive_keyword_counts(self) -> dict[str, Any]:
        result = self._fetch_one(POSITIVE_KEYWORD_COUNT_QUERY)
        return {
            "keyword_type": "positive",
            "matching_reviews": result.get("matching_reviews", 0),
        }
