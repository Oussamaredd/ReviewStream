import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.catalog import enrich_product_rows

SAMPLE_REVIEWS_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_reviews.csv"

POSITIVE_KEYWORDS = [
    "great",
    "excellent",
    "amazing",
    "good",
    "perfect",
    "love",
    "tasty",
    "fresh",
    "recommend",
]

NEGATIVE_KEYWORDS = [
    "bad",
    "terrible",
    "awful",
    "disappointed",
    "stale",
    "broken",
    "poor",
    "worst",
    "expired",
    "disgusting",
]


def classify_score(score: int) -> str:
    if score >= 4:
        return "positive"
    if score == 3:
        return "neutral"
    return "negative"


def keyword_pattern(keywords: list[str]) -> re.Pattern[str]:
    escaped = [re.escape(keyword.lower()) for keyword in keywords]
    return re.compile(rf"\b(?:{'|'.join(escaped)})\b")


POSITIVE_PATTERN = keyword_pattern(POSITIVE_KEYWORDS)
NEGATIVE_PATTERN = keyword_pattern(NEGATIVE_KEYWORDS)


def iso_from_unix(value: str) -> str:
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()


def word_count(text: str) -> int:
    normalized = " ".join(text.split())
    return len(normalized.split(" ")) if normalized else 0


def read_sample_reviews(path: Path = SAMPLE_REVIEWS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    reviews: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            score = int(row["Score"])
            text = row["Text"]
            reviews.append(
                {
                    "product_id": row["ProductId"],
                    "user_id": row["UserId"],
                    "score": score,
                    "sentiment": classify_score(score),
                    "text": text,
                    "source": "sample_csv",
                    "review_id": row["Id"],
                    "created_at": iso_from_unix(row["Time"]),
                    "text_length": len(text),
                    "word_count": word_count(text),
                    "has_negative_keywords": NEGATIVE_PATTERN.search(text.lower()) is not None,
                    "has_positive_keywords": POSITIVE_PATTERN.search(text.lower()) is not None,
                }
            )

    return reviews


def product_aggregates(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for review in reviews:
        grouped[review["product_id"]].append(review)

    rows = [
        {
            "product_id": product_id,
            "review_count": len(product_reviews),
            "average_score": sum(review["score"] for review in product_reviews)
            / len(product_reviews),
        }
        for product_id, product_reviews in grouped.items()
    ]
    return enrich_product_rows(rows)


def count_rows(counter: Counter[Any], label_key: str) -> list[dict[str, Any]]:
    return [
        {label_key: key, "review_count": count}
        for key, count in sorted(counter.items(), key=lambda item: item[0])
    ]


def build_sample_dashboard() -> dict[str, Any]:
    reviews = read_sample_reviews()
    sorted_reviews = sorted(reviews, key=lambda review: review["created_at"], reverse=True)
    product_rows = product_aggregates(reviews)
    total_reviews = len(reviews)
    average_score = (
        sum(review["score"] for review in reviews) / total_reviews if total_reviews else 0.0
    )

    negative_product_rows = []
    for product in product_rows:
        product_reviews = [
            review for review in reviews if review["product_id"] == product["product_id"]
        ]
        negative_count = sum(1 for review in product_reviews if review["sentiment"] == "negative")
        if negative_count:
            negative_product_rows.append({**product, "negative_review_count": negative_count})

    return {
        "summary": {
            "total_reviews": total_reviews,
            "average_score": average_score,
            "first_review_at": min((review["created_at"] for review in reviews), default=None),
            "last_review_at": max((review["created_at"] for review in reviews), default=None),
        },
        "sentiment": count_rows(Counter(review["sentiment"] for review in reviews), "sentiment"),
        "score_distribution": count_rows(Counter(review["score"] for review in reviews), "score"),
        "top_products": sorted(
            product_rows,
            key=lambda row: (row["average_score"], row["review_count"]),
            reverse=True,
        )[:10],
        "worst_products": sorted(
            product_rows,
            key=lambda row: (row["average_score"], -row["review_count"]),
        )[:10],
        "negative_products": sorted(
            negative_product_rows,
            key=lambda row: (row["negative_review_count"], -row["average_score"]),
            reverse=True,
        )[:10],
        "recent_reviews": enrich_product_rows(sorted_reviews[:20]),
        "sources": count_rows(Counter(review["source"] for review in reviews), "source"),
        "opinions": enrich_product_rows(sorted_reviews[:20]),
        "negative_keywords": {
            "keyword_type": "negative",
            "matching_reviews": sum(1 for review in reviews if review["has_negative_keywords"]),
        },
        "positive_keywords": {
            "keyword_type": "positive",
            "matching_reviews": sum(1 for review in reviews if review["has_positive_keywords"]),
        },
    }
