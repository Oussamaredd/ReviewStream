from dataclasses import dataclass
from typing import Any

from backend.reviewstream.analytics.application.errors import AnalyticsInputError
from backend.reviewstream.analytics.application.ports import AnalyticsRepository
from backend.reviewstream.analytics.application.types import SentimentFilter

MIN_LIMIT = 1
MAX_LIMIT = 100
MIN_REVIEWS_MIN = 1
MIN_REVIEWS_MAX = 1_000_000
VALID_SENTIMENTS = {"positive", "neutral", "negative"}


def validate_limit(value: int) -> int:
    if not MIN_LIMIT <= value <= MAX_LIMIT:
        raise AnalyticsInputError(f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}")
    return value


def validate_min_reviews(value: int) -> int:
    if not MIN_REVIEWS_MIN <= value <= MIN_REVIEWS_MAX:
        raise AnalyticsInputError(
            f"min_reviews must be between {MIN_REVIEWS_MIN} and {MIN_REVIEWS_MAX}"
        )
    return value


def validate_sentiment(value: SentimentFilter | None) -> SentimentFilter | None:
    if value is not None and value not in VALID_SENTIMENTS:
        raise AnalyticsInputError("sentiment must be positive, neutral, or negative")
    return value


@dataclass(frozen=True)
class AnalyticsQueryService:
    analytics_repository: AnalyticsRepository

    def fetch_summary(self) -> dict[str, Any]:
        return self.analytics_repository.fetch_summary()

    def fetch_sentiment_counts(self) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_sentiment_counts()

    def fetch_score_distribution(self) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_score_distribution()

    def fetch_product_scores(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_product_scores(validate_limit(limit))

    def fetch_top_products(self, limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_top_products(
            limit=validate_limit(limit),
            min_reviews=validate_min_reviews(min_reviews),
        )

    def fetch_worst_products(self, limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_worst_products(
            limit=validate_limit(limit),
            min_reviews=validate_min_reviews(min_reviews),
        )

    def fetch_recent_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_recent_reviews(validate_limit(limit))

    def fetch_opinions(
        self, limit: int = 50, sentiment: SentimentFilter | None = None
    ) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_opinions(
            limit=validate_limit(limit),
            sentiment=validate_sentiment(sentiment),
        )

    def fetch_negative_products(
        self, limit: int = 10, min_reviews: int = 3
    ) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_negative_products(
            limit=validate_limit(limit),
            min_reviews=validate_min_reviews(min_reviews),
        )

    def fetch_sources(self) -> list[dict[str, Any]]:
        return self.analytics_repository.fetch_sources()

    def fetch_negative_keyword_counts(self) -> dict[str, Any]:
        return self.analytics_repository.fetch_negative_keyword_counts()

    def fetch_positive_keyword_counts(self) -> dict[str, Any]:
        return self.analytics_repository.fetch_positive_keyword_counts()

    def fetch_dashboard(self) -> dict[str, Any]:
        return {
            "summary": self.fetch_summary(),
            "sentiment": self.fetch_sentiment_counts(),
            "score_distribution": self.fetch_score_distribution(),
            "top_products": self.fetch_top_products(limit=10, min_reviews=1),
            "worst_products": self.fetch_worst_products(limit=10, min_reviews=1),
            "negative_products": self.fetch_negative_products(limit=10, min_reviews=1),
            "recent_reviews": self.fetch_recent_reviews(limit=20),
            "sources": self.fetch_sources(),
            "opinions": self.fetch_opinions(limit=20),
            "negative_keywords": self.fetch_negative_keyword_counts(),
            "positive_keywords": self.fetch_positive_keyword_counts(),
        }
