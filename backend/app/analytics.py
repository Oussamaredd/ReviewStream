from fastapi import APIRouter, Query

from backend.app.hive_client import fetch_all, fetch_one

router = APIRouter(prefix="/analytics", tags=["analytics"])


def fetch_summary() -> dict:
    return fetch_one("""
        SELECT
            COUNT(*) AS total_reviews,
            AVG(score) AS average_score,
            MIN(created_at) AS first_review_at,
            MAX(created_at) AS last_review_at
        FROM reviews_enriched
        """)


def fetch_sentiment_counts() -> list[dict]:
    return fetch_all("""
        SELECT
            sentiment,
            COUNT(*) AS review_count
        FROM reviews_enriched
        GROUP BY sentiment
        """)


def fetch_product_scores(limit: int = 10) -> list[dict]:
    return fetch_all(f"""
        SELECT
            product_id,
            COUNT(*) AS review_count,
            AVG(score) AS average_score
        FROM reviews_enriched
        GROUP BY product_id
        ORDER BY review_count DESC, average_score DESC
        LIMIT {limit}
        """)


@router.get("/summary")
def get_summary() -> dict:
    return fetch_summary()


@router.get("/sentiment")
def get_sentiment_counts() -> list[dict]:
    return fetch_sentiment_counts()


@router.get("/products")
def get_product_scores(limit: int = Query(default=10, ge=1, le=100)) -> list[dict]:
    return fetch_product_scores(limit)


@router.get("")
@router.get("/")
def get_analytics() -> dict:
    return {
        "summary": fetch_summary(),
        "sentiment": fetch_sentiment_counts(),
        "products": fetch_product_scores(limit=10),
    }
