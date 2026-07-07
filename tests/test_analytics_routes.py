from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.reviewstream.analytics.application.errors import AnalyticsUnavailableError
from backend.reviewstream.analytics.infrastructure import hive_analytics_repository
from backend.reviewstream.main import app
from backend.reviewstream.platform.config import Settings, settings
from backend.reviewstream.platform.hive_client import HiveQueryError

client = TestClient(app)

SUMMARY_RESPONSE = {
    "total_reviews": 6,
    "average_score": 4.0,
    "first_review_at": "2026-01-01T00:00:00",
    "last_review_at": "2026-01-02T00:00:00",
}

SENTIMENT_RESPONSE = [
    {"sentiment": "negative", "review_count": 1},
    {"sentiment": "neutral", "review_count": 1},
    {"sentiment": "positive", "review_count": 4},
]

PRODUCT_RESPONSE = [
    {"product_id": "P001", "review_count": 3, "average_score": 4.67},
    {"product_id": "P002", "review_count": 1, "average_score": 3.0},
]

SCORE_DISTRIBUTION_RESPONSE = [
    {"score": 1, "review_count": 1},
    {"score": 3, "review_count": 1},
    {"score": 5, "review_count": 4},
]

TOP_PRODUCTS_RESPONSE = [
    {"product_id": "P001", "review_count": 12, "average_score": 4.9},
]

WORST_PRODUCTS_RESPONSE = [
    {"product_id": "P009", "review_count": 7, "average_score": 1.7},
]

NEGATIVE_PRODUCTS_RESPONSE = [
    {
        "product_id": "P009",
        "negative_review_count": 5,
        "review_count": 7,
        "average_score": 1.7,
    },
]

RECENT_RESPONSE = [
    {
        "product_id": "P001",
        "user_id": "client1",
        "score": 5,
        "sentiment": "positive",
        "text": "Great and fresh",
        "source": "web",
        "review_id": "review-1",
        "created_at": "2026-01-02T00:00:00",
        "text_length": 15,
        "word_count": 3,
        "has_negative_keywords": False,
        "has_positive_keywords": True,
    },
]

SOURCES_RESPONSE = [
    {"source": "amazon_csv", "review_count": 5},
    {"source": "web", "review_count": 1},
]

NEGATIVE_KEYWORDS_RESPONSE = {
    "keyword_type": "negative",
    "matching_reviews": 2,
}

POSITIVE_KEYWORDS_RESPONSE = {
    "keyword_type": "positive",
    "matching_reviews": 4,
}


@pytest.fixture(autouse=True)
def reset_dashboard_cache() -> None:
    app.state.container.dashboard_cache.clear()


def get_cached_dashboard() -> dict[str, Any] | None:
    return app.state.container.dashboard_cache.get()


def enrich_product_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return app.state.container.catalog_service.enrich_product_rows(rows)


def mock_hive_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    queries: list[str] = []

    def fake_fetch_one(query: str, app_settings: Settings | None = None) -> dict[str, Any]:
        queries.append(query)
        assert "FROM reviews_enriched" in query

        if "has_negative_keywords = true" in query:
            return {"matching_reviews": 2}

        if "has_positive_keywords = true" in query:
            return {"matching_reviews": 4}

        assert "COUNT(*) AS total_reviews" in query
        return SUMMARY_RESPONSE

    def fake_fetch_all(query: str, app_settings: Settings | None = None) -> list[dict[str, Any]]:
        queries.append(query)
        assert "FROM reviews_enriched" in query

        if "GROUP BY sentiment" in query:
            return SENTIMENT_RESPONSE

        if "GROUP BY score" in query:
            return SCORE_DISTRIBUTION_RESPONSE

        if "negative_review_count" in query:
            return NEGATIVE_PRODUCTS_RESPONSE

        if "ORDER BY created_at DESC" in query:
            return RECENT_RESPONSE

        if "GROUP BY COALESCE(source, 'unknown')" in query:
            return SOURCES_RESPONSE

        if "GROUP BY product_id" in query and "HAVING COUNT(*) >=" in query:
            if "ORDER BY average_score DESC" in query:
                return TOP_PRODUCTS_RESPONSE
            if "ORDER BY average_score ASC" in query:
                return WORST_PRODUCTS_RESPONSE

        if "GROUP BY product_id" in query:
            return PRODUCT_RESPONSE

        raise AssertionError(f"Unexpected analytics query: {query}")

    monkeypatch.setattr(hive_analytics_repository, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(hive_analytics_repository, "fetch_all", fake_fetch_all)
    return queries


def test_health_returns_status_and_topic() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "kafka_topic": settings.kafka_topic}


def test_kafka_health_returns_probe_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app.state.container.health_service.kafka_probe,
        "probe",
        lambda: {
            "status": "ok",
            "available": True,
            "bootstrap_servers": ["127.0.0.1:9092"],
            "topic": "reviews",
        },
    )

    response = client.get("/health/kafka")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "available": True,
        "bootstrap_servers": ["127.0.0.1:9092"],
        "topic": "reviews",
    }


def test_existing_analytics_endpoints_return_hive_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries = mock_hive_calls(monkeypatch)

    assert client.get("/analytics/summary").json() == SUMMARY_RESPONSE
    assert client.get("/analytics/sentiment").json() == SENTIMENT_RESPONSE
    assert client.get("/analytics/products?limit=3").json() == enrich_product_rows(PRODUCT_RESPONSE)
    assert client.get("/analytics").json() == {
        "summary": SUMMARY_RESPONSE,
        "sentiment": SENTIMENT_RESPONSE,
        "products": enrich_product_rows(PRODUCT_RESPONSE),
    }
    assert "LIMIT 3" in "\n".join(queries)
    assert "LIMIT 10" in queries[-1]


def test_new_analytics_endpoints_return_hive_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    queries = mock_hive_calls(monkeypatch)

    assert client.get("/analytics/score-distribution").json() == SCORE_DISTRIBUTION_RESPONSE
    assert client.get(
        "/analytics/top-products?limit=4&min_reviews=2"
    ).json() == enrich_product_rows(TOP_PRODUCTS_RESPONSE)
    assert client.get(
        "/analytics/worst-products?limit=4&min_reviews=2"
    ).json() == enrich_product_rows(WORST_PRODUCTS_RESPONSE)
    assert client.get("/analytics/recent?limit=5").json() == enrich_product_rows(RECENT_RESPONSE)
    assert client.get("/analytics/opinions?limit=7").json() == enrich_product_rows(RECENT_RESPONSE)
    assert client.get(
        "/analytics/opinions?limit=8&sentiment=positive"
    ).json() == enrich_product_rows(RECENT_RESPONSE)
    assert client.get(
        "/analytics/negative-products?limit=6&min_reviews=3"
    ).json() == enrich_product_rows(NEGATIVE_PRODUCTS_RESPONSE)
    assert client.get("/analytics/sources").json() == SOURCES_RESPONSE
    assert client.get("/analytics/keywords/negative").json() == NEGATIVE_KEYWORDS_RESPONSE
    assert client.get("/analytics/keywords/positive").json() == POSITIVE_KEYWORDS_RESPONSE

    joined_queries = "\n".join(queries)
    assert "LIMIT 4" in joined_queries
    assert "HAVING COUNT(*) >= 2" in joined_queries
    assert "LIMIT 5" in joined_queries
    assert "LIMIT 7" in joined_queries
    assert "LIMIT 8" in joined_queries
    assert "sentiment = 'positive'" in joined_queries
    assert "LIMIT 6" in joined_queries


def test_dashboard_endpoint_payload_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_hive_calls(monkeypatch)

    response = client.get("/analytics/dashboard?prefer_cache=false&allow_sample=false")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fresh"
    assert payload["stale"] is False
    assert payload["generated_at"]
    assert payload["summary"] == SUMMARY_RESPONSE
    assert payload["sentiment"] == SENTIMENT_RESPONSE
    assert payload["score_distribution"] == SCORE_DISTRIBUTION_RESPONSE
    assert payload["top_products"] == enrich_product_rows(TOP_PRODUCTS_RESPONSE)
    assert payload["worst_products"] == enrich_product_rows(WORST_PRODUCTS_RESPONSE)
    assert payload["negative_products"] == enrich_product_rows(NEGATIVE_PRODUCTS_RESPONSE)
    assert payload["recent_reviews"] == enrich_product_rows(RECENT_RESPONSE)
    assert payload["sources"] == SOURCES_RESPONSE
    assert payload["opinions"] == enrich_product_rows(RECENT_RESPONSE)
    assert payload["negative_keywords"] == NEGATIVE_KEYWORDS_RESPONSE
    assert payload["positive_keywords"] == POSITIVE_KEYWORDS_RESPONSE
    assert get_cached_dashboard() == payload


def test_dashboard_returns_cached_payload_when_hive_fails_after_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_hive_calls(monkeypatch)
    fresh_response = client.get("/analytics/dashboard?prefer_cache=false&allow_sample=false")
    assert fresh_response.status_code == 200

    def failing_fetch_dashboard() -> dict[str, Any]:
        raise AnalyticsUnavailableError("analytics store unavailable")

    monkeypatch.setattr(
        app.state.container.dashboard_service, "fetch_dashboard", failing_fetch_dashboard
    )

    cached_response = client.get("/analytics/dashboard")

    assert cached_response.status_code == 200
    payload = cached_response.json()
    assert payload["status"] == "cached"
    assert payload["stale"] is True
    assert payload["warning"] == "Hive is unavailable. Showing last successful analytics snapshot."
    assert payload["generated_at"] == fresh_response.json()["generated_at"]
    assert payload["summary"] == fresh_response.json()["summary"]


def test_dashboard_fast_mode_returns_cached_payload_without_blocking_on_hive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_hive_calls(monkeypatch)
    fresh_response = client.get("/analytics/dashboard?prefer_cache=false&allow_sample=false")
    assert fresh_response.status_code == 200

    monkeypatch.setattr(app.state.container.dashboard_service, "refresh_dashboard_cache", lambda: None)
    monkeypatch.setattr(
        app.state.container.dashboard_service,
        "fetch_dashboard",
        lambda: pytest.fail("Fast cached dashboard should not block on Hive"),
    )

    response = client.get("/analytics/dashboard?prefer_cache=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "cached"
    assert payload["stale"] is True
    assert payload["summary"] == fresh_response.json()["summary"]


def test_dashboard_returns_503_when_hive_fails_and_cache_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_fetch_dashboard() -> dict[str, Any]:
        raise AnalyticsUnavailableError("analytics store unavailable")

    monkeypatch.setattr(
        app.state.container.dashboard_service, "fetch_dashboard", failing_fetch_dashboard
    )

    response = client.get("/analytics/dashboard?prefer_cache=false&allow_sample=false")

    assert response.status_code == 503
    assert response.json() == {"detail": "Analytics service is unavailable"}


def test_dashboard_defaults_to_sample_when_hive_fails_and_cache_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_fetch_dashboard() -> dict[str, Any]:
        raise AnalyticsUnavailableError("analytics store unavailable")

    monkeypatch.setattr(app.state.container.dashboard_service, "refresh_dashboard_cache", lambda: None)
    monkeypatch.setattr(
        app.state.container.dashboard_service, "fetch_dashboard", failing_fetch_dashboard
    )

    response = client.get("/analytics/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sample"
    assert payload["stale"] is True
    assert payload["summary"]["total_reviews"] == 16


def test_dashboard_cache_miss_fetches_fresh_hive_before_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_hive_calls(monkeypatch)

    response = client.get("/analytics/dashboard?prefer_cache=true&allow_sample=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fresh"
    assert payload["stale"] is False
    assert payload["summary"] == SUMMARY_RESPONSE
    assert get_cached_dashboard() == payload


def test_hive_repository_uses_injected_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    injected_settings = Settings(hive_host="custom-hive-host")
    captured_settings: list[Settings | None] = []

    def fake_fetch_one(query: str, app_settings: Settings | None = None) -> dict[str, Any]:
        captured_settings.append(app_settings)
        return SUMMARY_RESPONSE

    monkeypatch.setattr(hive_analytics_repository, "fetch_one", fake_fetch_one)

    repository = hive_analytics_repository.HiveAnalyticsRepository(
        enrich_product_rows,
        injected_settings,
    )

    assert repository.fetch_summary() == SUMMARY_RESPONSE
    assert captured_settings == [injected_settings]


def test_dashboard_background_refresh_is_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refresh_called = False

    def mark_refresh_called() -> None:
        nonlocal refresh_called
        refresh_called = True

    monkeypatch.delenv("DASHBOARD_BACKGROUND_REFRESH_ENABLED", raising=False)
    monkeypatch.setattr(
        app.state.container.dashboard_service, "refresh_dashboard_cache", mark_refresh_called
    )

    app.state.container.dashboard_service.schedule_dashboard_refresh()

    assert refresh_called is False


def test_empty_dashboard_responses_are_valid_and_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    def empty_fetch_dashboard() -> dict[str, Any]:
        return {
            "summary": {
                "total_reviews": None,
                "average_score": None,
                "first_review_at": None,
                "last_review_at": None,
            },
            "sentiment": [],
            "score_distribution": [],
            "top_products": [],
            "worst_products": [],
            "negative_products": [],
            "recent_reviews": [],
            "sources": [],
            "opinions": [],
            "negative_keywords": {"keyword_type": "negative", "matching_reviews": None},
            "positive_keywords": {"keyword_type": "positive", "matching_reviews": None},
        }

    monkeypatch.setattr(
        app.state.container.dashboard_service, "fetch_dashboard", empty_fetch_dashboard
    )

    response = client.get("/analytics/dashboard?prefer_cache=false&allow_sample=false")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {
        "total_reviews": 0,
        "average_score": 0.0,
        "first_review_at": None,
        "last_review_at": None,
    }
    assert payload["sentiment"] == []
    assert payload["score_distribution"] == []
    assert payload["top_products"] == []
    assert payload["worst_products"] == []
    assert payload["negative_products"] == []
    assert payload["recent_reviews"] == []
    assert payload["sources"] == []
    assert payload["opinions"] == []
    assert payload["negative_keywords"]["matching_reviews"] == 0
    assert payload["positive_keywords"]["matching_reviews"] == 0


def test_dashboard_cache_stores_only_valid_successful_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app.state.container.dashboard_service,
        "fetch_dashboard",
        lambda: {"summary": SUMMARY_RESPONSE},
    )

    response = client.get("/analytics/dashboard?prefer_cache=false&allow_sample=false")

    assert response.status_code == 503
    assert response.json() == {"detail": "Analytics service is unavailable"}
    assert get_cached_dashboard() is None


@pytest.mark.parametrize(
    "path",
    [
        "/analytics/products?limit=0",
        "/analytics/products?limit=101",
        "/analytics/top-products?limit=0",
        "/analytics/top-products?min_reviews=0",
        "/analytics/worst-products?limit=101",
        "/analytics/worst-products?min_reviews=0",
        "/analytics/recent?limit=0",
        "/analytics/recent?limit=101",
        "/analytics/opinions?limit=0",
        "/analytics/opinions?limit=101",
        "/analytics/opinions?sentiment=angry",
        "/analytics/negative-products?limit=0",
        "/analytics/negative-products?min_reviews=0",
    ],
)
def test_analytics_rejects_invalid_query_params(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    def fail_if_hive_is_called(query: str) -> list[dict[str, Any]]:
        raise AssertionError(f"Hive should not be called for invalid params: {query}")

    monkeypatch.setattr(hive_analytics_repository, "fetch_all", fail_if_hive_is_called)

    response = client.get(path)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("path", "failing_mock"),
    [
        ("/analytics/summary", "fetch_one"),
        ("/analytics/sentiment", "fetch_all"),
        ("/analytics/products", "fetch_all"),
        ("/analytics/score-distribution", "fetch_all"),
        ("/analytics/top-products", "fetch_all"),
        ("/analytics/worst-products", "fetch_all"),
        ("/analytics/recent", "fetch_all"),
        ("/analytics/opinions", "fetch_all"),
        ("/analytics/negative-products", "fetch_all"),
        ("/analytics/sources", "fetch_all"),
        ("/analytics/keywords/negative", "fetch_one"),
        ("/analytics/keywords/positive", "fetch_one"),
        ("/analytics/dashboard?prefer_cache=false&allow_sample=false", "fetch_one"),
        ("/analytics", "fetch_one"),
    ],
)
def test_hive_errors_return_safe_analytics_detail(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    failing_mock: str,
) -> None:
    def failing_fetch_one(query: str, app_settings: Settings | None = None) -> dict[str, Any]:
        raise HiveQueryError("internal thrift connection failed")

    def failing_fetch_all(query: str, app_settings: Settings | None = None) -> list[dict[str, Any]]:
        raise HiveQueryError("internal thrift connection failed")

    def fallback_fetch_one(query: str, app_settings: Settings | None = None) -> dict[str, Any]:
        return SUMMARY_RESPONSE

    def fallback_fetch_all(query: str, app_settings: Settings | None = None) -> list[dict[str, Any]]:
        return PRODUCT_RESPONSE

    monkeypatch.setattr(
        hive_analytics_repository,
        "fetch_one",
        failing_fetch_one if failing_mock == "fetch_one" else fallback_fetch_one,
    )
    monkeypatch.setattr(
        hive_analytics_repository,
        "fetch_all",
        failing_fetch_all if failing_mock == "fetch_all" else fallback_fetch_all,
    )

    response = client.get(path)

    assert response.status_code == 503
    assert response.json() == {"detail": "Analytics service is unavailable"}
    assert "internal thrift connection failed" not in response.text
