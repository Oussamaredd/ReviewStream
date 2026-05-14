from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app import analytics
from backend.app.config import settings
from backend.app.hive_client import HiveQueryError
from backend.app.main import app

client = TestClient(app)

SUMMARY_RESPONSE = {
    "total_reviews": 4,
    "average_score": 4.25,
    "first_review_at": "2026-01-01T00:00:00",
    "last_review_at": "2026-01-02T00:00:00",
}

SENTIMENT_RESPONSE = [
    {"sentiment": "positive", "review_count": 3},
    {"sentiment": "neutral", "review_count": 1},
]

PRODUCT_RESPONSE = [
    {"product_id": "P001", "review_count": 3, "average_score": 4.67},
    {"product_id": "P002", "review_count": 1, "average_score": 3.0},
]


def mock_hive_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    queries: list[str] = []

    def fake_fetch_one(query: str) -> dict[str, Any]:
        queries.append(query)
        assert "FROM reviews_enriched" in query
        assert "COUNT(*) AS total_reviews" in query
        return SUMMARY_RESPONSE

    def fake_fetch_all(query: str) -> list[dict[str, Any]]:
        queries.append(query)
        assert "FROM reviews_enriched" in query

        if "GROUP BY sentiment" in query:
            return SENTIMENT_RESPONSE

        if "GROUP BY product_id" in query:
            return PRODUCT_RESPONSE

        raise AssertionError(f"Unexpected analytics query: {query}")

    monkeypatch.setattr(analytics, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(analytics, "fetch_all", fake_fetch_all)
    return queries


def test_health_returns_status_and_topic() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "kafka_topic": settings.kafka_topic}


def test_summary_returns_hive_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_hive_calls(monkeypatch)

    response = client.get("/analytics/summary")

    assert response.status_code == 200
    assert response.json() == SUMMARY_RESPONSE


def test_sentiment_returns_hive_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_hive_calls(monkeypatch)

    response = client.get("/analytics/sentiment")

    assert response.status_code == 200
    assert response.json() == SENTIMENT_RESPONSE


def test_products_returns_hive_scores_with_constrained_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries = mock_hive_calls(monkeypatch)

    response = client.get("/analytics/products?limit=3")

    assert response.status_code == 200
    assert response.json() == PRODUCT_RESPONSE
    assert "LIMIT 3" in queries[-1]


def test_products_rejects_limits_outside_allowed_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_hive_is_called(query: str) -> list[dict[str, Any]]:
        raise AssertionError(f"Hive should not be called for invalid limit: {query}")

    monkeypatch.setattr(analytics, "fetch_all", fail_if_hive_is_called)

    low_response = client.get("/analytics/products?limit=0")
    high_response = client.get("/analytics/products?limit=101")

    assert low_response.status_code == 422
    assert high_response.status_code == 422


def test_aggregate_returns_combined_hive_analytics(monkeypatch: pytest.MonkeyPatch) -> None:
    queries = mock_hive_calls(monkeypatch)

    response = client.get("/analytics")

    assert response.status_code == 200
    assert response.json() == {
        "summary": SUMMARY_RESPONSE,
        "sentiment": SENTIMENT_RESPONSE,
        "products": PRODUCT_RESPONSE,
    }
    assert "LIMIT 10" in queries[-1]


@pytest.mark.parametrize(
    ("path", "failing_mock"),
    [
        ("/analytics/summary", "fetch_one"),
        ("/analytics/sentiment", "fetch_all"),
        ("/analytics/products", "fetch_all"),
        ("/analytics", "fetch_one"),
    ],
)
def test_hive_errors_return_safe_analytics_detail(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    failing_mock: str,
) -> None:
    def failing_fetch_one(query: str) -> dict[str, Any]:
        raise HiveQueryError("internal thrift connection failed")

    def failing_fetch_all(query: str) -> list[dict[str, Any]]:
        raise HiveQueryError("internal thrift connection failed")

    fallback_fetch_one: Callable[[str], dict[str, Any]] = lambda query: SUMMARY_RESPONSE
    fallback_fetch_all: Callable[[str], list[dict[str, Any]]] = lambda query: PRODUCT_RESPONSE

    monkeypatch.setattr(
        analytics,
        "fetch_one",
        failing_fetch_one if failing_mock == "fetch_one" else fallback_fetch_one,
    )
    monkeypatch.setattr(
        analytics,
        "fetch_all",
        failing_fetch_all if failing_mock == "fetch_all" else fallback_fetch_all,
    )

    response = client.get(path)

    assert response.status_code == 503
    assert response.json() == {"detail": "Analytics service is unavailable"}
    assert "internal thrift connection failed" not in response.text
