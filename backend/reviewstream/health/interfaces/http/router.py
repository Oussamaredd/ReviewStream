from fastapi import APIRouter

from backend.reviewstream.health.application.checks import HealthService
from backend.reviewstream.health.interfaces.http.responses import (
    HealthResponse,
    KafkaHealthResponse,
    RootResponse,
)


def create_router(health_service: HealthService) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/", response_model=RootResponse)
    def root() -> RootResponse:
        return RootResponse(
            app="ReviewStream API",
            status="running",
        )

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(**health_service.summary())

    @router.get(
        "/health/kafka", response_model=KafkaHealthResponse, response_model_exclude_none=True
    )
    def kafka_health() -> KafkaHealthResponse:
        return KafkaHealthResponse.from_mapping(health_service.kafka())

    return router
