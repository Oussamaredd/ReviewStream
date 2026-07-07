from typing import Any, Protocol

from backend.reviewstream.analytics.application.types import SentimentFilter


class AnalyticsRepository(Protocol):
    def fetch_summary(self) -> dict[str, Any]:
        """Return aggregate review summary metrics."""

    def fetch_sentiment_counts(self) -> list[dict[str, Any]]:
        """Return review counts grouped by sentiment."""

    def fetch_score_distribution(self) -> list[dict[str, Any]]:
        """Return review counts grouped by numeric score."""

    def fetch_product_scores(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return review aggregates grouped by product."""

    def fetch_top_products(self, limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
        """Return highest-rated products."""

    def fetch_worst_products(self, limit: int = 10, min_reviews: int = 5) -> list[dict[str, Any]]:
        """Return lowest-rated products."""

    def fetch_recent_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return newest review rows."""

    def fetch_opinions(
        self, limit: int = 50, sentiment: SentimentFilter | None = None
    ) -> list[dict[str, Any]]:
        """Return review text rows, optionally filtered by sentiment."""

    def fetch_negative_products(
        self, limit: int = 10, min_reviews: int = 3
    ) -> list[dict[str, Any]]:
        """Return products with negative review counts."""

    def fetch_sources(self) -> list[dict[str, Any]]:
        """Return review counts grouped by source."""

    def fetch_negative_keyword_counts(self) -> dict[str, Any]:
        """Return count of reviews matching negative keywords."""

    def fetch_positive_keyword_counts(self) -> dict[str, Any]:
        """Return count of reviews matching positive keywords."""


class DashboardCache(Protocol):
    def get(self) -> dict[str, Any] | None:
        """Return the latest dashboard snapshot."""

    def set(self, data: dict[str, Any]) -> None:
        """Store a dashboard snapshot."""

    def clear(self) -> None:
        """Clear the dashboard snapshot."""


class SampleDashboardProvider(Protocol):
    def build_dashboard(self) -> dict[str, Any]:
        """Build a local sample dashboard payload."""
