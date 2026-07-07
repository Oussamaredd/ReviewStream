from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Protocol

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.reviewstream.analytics.application.dashboard_service import DashboardService
from backend.reviewstream.analytics.application.ports import DashboardCache
from backend.reviewstream.analytics.application.queries import AnalyticsQueryService
from backend.reviewstream.analytics.infrastructure.dashboard_cache import InMemoryDashboardCache
from backend.reviewstream.analytics.infrastructure.hive_analytics_repository import (
    HiveAnalyticsRepository,
)
from backend.reviewstream.analytics.infrastructure.sample_dashboard import (
    CsvSampleDashboardProvider,
)
from backend.reviewstream.analytics.interfaces.http.router import (
    create_router as create_analytics_router,
)
from backend.reviewstream.catalog.application.queries import CatalogQueryService
from backend.reviewstream.catalog.infrastructure.in_memory_catalog_repository import (
    InMemoryCatalogRepository,
)
from backend.reviewstream.catalog.interfaces.http.router import (
    create_router as create_catalog_router,
)
from backend.reviewstream.health.application.checks import HealthService
from backend.reviewstream.health.application.ports import KafkaProbe
from backend.reviewstream.health.infrastructure.kafka_health_probe import KafkaHealthProbe
from backend.reviewstream.health.interfaces.http.router import create_router as create_health_router
from backend.reviewstream.platform.config import Settings
from backend.reviewstream.reviews.application.use_cases import (
    SubmitProductReviewUseCase,
    SubmitReviewUseCase,
)
from backend.reviewstream.reviews.application.ports import ReviewPublisher
from backend.reviewstream.reviews.infrastructure.kafka_review_publisher import KafkaReviewPublisher
from backend.reviewstream.reviews.interfaces.http.router import (
    create_router as create_reviews_router,
)


class ManagedReviewPublisher(ReviewPublisher, KafkaProbe, Protocol):
    def close(self) -> None:
        """Release publisher resources."""


@dataclass
class ApplicationContainer:
    settings: Settings
    catalog_service: CatalogQueryService
    review_publisher: ManagedReviewPublisher
    submit_review: SubmitReviewUseCase
    submit_product_review: SubmitProductReviewUseCase
    analytics_service: AnalyticsQueryService
    dashboard_cache: DashboardCache
    dashboard_service: DashboardService
    health_service: HealthService


def build_container(app_settings: Settings | None = None) -> ApplicationContainer:
    if app_settings is None:
        app_settings = Settings.from_env()

    catalog_repository = InMemoryCatalogRepository()
    catalog_service = CatalogQueryService(catalog_repository)

    review_publisher = KafkaReviewPublisher(app_settings)
    submit_review = SubmitReviewUseCase(review_publisher)
    submit_product_review = SubmitProductReviewUseCase(catalog_service, submit_review)

    analytics_repository = HiveAnalyticsRepository(
        catalog_service.enrich_product_rows, app_settings
    )
    analytics_service = AnalyticsQueryService(analytics_repository)
    dashboard_cache = InMemoryDashboardCache()
    sample_dashboard_provider = CsvSampleDashboardProvider(catalog_service.enrich_product_rows)
    dashboard_service = DashboardService(
        analytics_service=analytics_service,
        cache=dashboard_cache,
        sample_dashboard_provider=sample_dashboard_provider,
    )

    health_service = HealthService(
        settings=app_settings,
        kafka_probe=KafkaHealthProbe(review_publisher.probe),
    )

    return ApplicationContainer(
        settings=app_settings,
        catalog_service=catalog_service,
        review_publisher=review_publisher,
        submit_review=submit_review,
        submit_product_review=submit_product_review,
        analytics_service=analytics_service,
        dashboard_cache=dashboard_cache,
        dashboard_service=dashboard_service,
        health_service=health_service,
    )


def create_lifespan(container: ApplicationContainer):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        container.review_publisher.close()

    return lifespan


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    if container is None:
        container = build_container()

    app = FastAPI(
        title="ReviewStream API",
        version="0.1.0",
        lifespan=create_lifespan(container),
    )
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(create_health_router(container.health_service))
    app.include_router(create_catalog_router(container.catalog_service))
    app.include_router(
        create_reviews_router(container.submit_review, container.submit_product_review)
    )
    app.include_router(
        create_analytics_router(container.analytics_service, container.dashboard_service)
    )

    return app
