import logging
from collections.abc import Callable
from typing import Annotated, Any, TypeVar

from fastapi import APIRouter, HTTPException, Query

from backend.reviewstream.analytics.application.dashboard_payloads import DashboardPayloadError
from backend.reviewstream.analytics.application.dashboard_service import DashboardService
from backend.reviewstream.analytics.application.errors import (
    AnalyticsInputError,
    AnalyticsUnavailableError,
)
from backend.reviewstream.analytics.application.queries import AnalyticsQueryService
from backend.reviewstream.analytics.application.types import SentimentFilter

logger = logging.getLogger(__name__)
T = TypeVar("T")

ANALYTICS_UNAVAILABLE_DETAIL = "Analytics service is unavailable"

Limit = Annotated[int, Query(ge=1, le=100)]
RecentLimit = Annotated[int, Query(ge=1, le=100)]
MinReviews = Annotated[int, Query(ge=1, le=1_000_000)]


def create_router(
    analytics_service: AnalyticsQueryService,
    dashboard_service: DashboardService,
) -> APIRouter:
    router = APIRouter(prefix="/analytics", tags=["analytics"])

    def analytics_response(operation: str, query: Callable[[], T]) -> T:
        try:
            return query()
        except AnalyticsUnavailableError as error:
            logger.exception("Analytics Hive query failed during %s", operation)
            raise HTTPException(status_code=503, detail=ANALYTICS_UNAVAILABLE_DETAIL) from error
        except AnalyticsInputError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.get("/summary")
    def get_summary() -> dict[str, Any]:
        return analytics_response("summary", analytics_service.fetch_summary)

    @router.get("/sentiment")
    def get_sentiment_counts() -> list[dict[str, Any]]:
        return analytics_response("sentiment", analytics_service.fetch_sentiment_counts)

    @router.get("/products")
    def get_product_scores(limit: Limit = 10) -> list[dict[str, Any]]:
        return analytics_response("products", lambda: analytics_service.fetch_product_scores(limit))

    @router.get("/score-distribution")
    def get_score_distribution() -> list[dict[str, Any]]:
        return analytics_response("score_distribution", analytics_service.fetch_score_distribution)

    @router.get("/top-products")
    def get_top_products(limit: Limit = 10, min_reviews: MinReviews = 5) -> list[dict[str, Any]]:
        return analytics_response(
            "top_products",
            lambda: analytics_service.fetch_top_products(limit=limit, min_reviews=min_reviews),
        )

    @router.get("/worst-products")
    def get_worst_products(limit: Limit = 10, min_reviews: MinReviews = 5) -> list[dict[str, Any]]:
        return analytics_response(
            "worst_products",
            lambda: analytics_service.fetch_worst_products(limit=limit, min_reviews=min_reviews),
        )

    @router.get("/recent")
    def get_recent_reviews(limit: RecentLimit = 20) -> list[dict[str, Any]]:
        return analytics_response(
            "recent_reviews", lambda: analytics_service.fetch_recent_reviews(limit)
        )

    @router.get("/opinions")
    def get_opinions(
        limit: Limit = 50,
        sentiment: Annotated[SentimentFilter | None, Query()] = None,
    ) -> list[dict[str, Any]]:
        return analytics_response(
            "opinions",
            lambda: analytics_service.fetch_opinions(limit=limit, sentiment=sentiment),
        )

    @router.get("/negative-products")
    def get_negative_products(
        limit: Limit = 10, min_reviews: MinReviews = 3
    ) -> list[dict[str, Any]]:
        return analytics_response(
            "negative_products",
            lambda: analytics_service.fetch_negative_products(limit=limit, min_reviews=min_reviews),
        )

    @router.get("/sources")
    def get_sources() -> list[dict[str, Any]]:
        return analytics_response("sources", analytics_service.fetch_sources)

    @router.get("/keywords/negative")
    def get_negative_keyword_counts() -> dict[str, Any]:
        return analytics_response(
            "negative_keywords", analytics_service.fetch_negative_keyword_counts
        )

    @router.get("/keywords/positive")
    def get_positive_keyword_counts() -> dict[str, Any]:
        return analytics_response(
            "positive_keywords", analytics_service.fetch_positive_keyword_counts
        )

    @router.get("/dashboard")
    def get_dashboard(
        prefer_cache: bool = True,
        allow_sample: bool = True,
    ) -> dict[str, Any]:
        try:
            return dashboard_service.dashboard_response(
                prefer_cache=prefer_cache, allow_sample=allow_sample
            )
        except AnalyticsUnavailableError as error:
            raise HTTPException(status_code=503, detail=ANALYTICS_UNAVAILABLE_DETAIL) from error
        except AnalyticsInputError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except DashboardPayloadError as error:
            logger.exception("Analytics dashboard payload was not safe to cache")
            raise HTTPException(status_code=503, detail=ANALYTICS_UNAVAILABLE_DETAIL) from error

    @router.get("")
    @router.get("/")
    def get_analytics() -> dict[str, Any]:
        return analytics_response(
            "aggregate",
            lambda: {
                "summary": analytics_service.fetch_summary(),
                "sentiment": analytics_service.fetch_sentiment_counts(),
                "products": analytics_service.fetch_product_scores(limit=10),
            },
        )

    return router
