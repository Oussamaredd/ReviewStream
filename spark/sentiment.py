import re
from collections.abc import Sequence
from typing import Any

from pyspark.sql.functions import (
    coalesce,
    col,
    length,
    lit,
    lower,
    regexp_replace,
    size,
    split,
    trim,
    when,
)

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


def keyword_pattern(keywords: Sequence[str]) -> str:
    escaped = [re.escape(keyword.lower()) for keyword in keywords]
    return rf"\b(?:{'|'.join(escaped)})\b"


def has_any_keyword(text: str, keywords: Sequence[str]) -> bool:
    return re.search(keyword_pattern(keywords), text.lower()) is not None


def add_sentiment(reviews: Any) -> Any:
    return reviews.withColumn(
        "sentiment",
        when(col("score") >= 4, "positive")
        .when(col("score") == 3, "neutral")
        .otherwise("negative"),
    )


def add_text_features(reviews: Any) -> Any:
    safe_text = coalesce(col("text").cast("string"), lit(""))
    normalized_text = lower(safe_text)
    trimmed_text = trim(safe_text)
    normalized_spaces = regexp_replace(trimmed_text, r"\s+", " ")

    return (
        reviews.withColumn("text_length", length(safe_text).cast("int"))
        .withColumn(
            "word_count",
            when(length(trimmed_text) == 0, lit(0))
            .otherwise(size(split(normalized_spaces, " ")))
            .cast("int"),
        )
        .withColumn(
            "has_negative_keywords", normalized_text.rlike(keyword_pattern(NEGATIVE_KEYWORDS))
        )
        .withColumn(
            "has_positive_keywords", normalized_text.rlike(keyword_pattern(POSITIVE_KEYWORDS))
        )
    )


def enrich_reviews(reviews: Any) -> Any:
    return add_text_features(add_sentiment(reviews))
