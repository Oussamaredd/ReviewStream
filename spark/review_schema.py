from typing import Any

from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

REVIEW_EVENT_SCHEMA = StructType(
    [
        StructField("product_id", StringType(), nullable=False),
        StructField("user_id", StringType(), nullable=False),
        StructField("score", IntegerType(), nullable=False),
        StructField("text", StringType(), nullable=False),
        StructField("source", StringType(), nullable=True),
        StructField("review_id", StringType(), nullable=False),
        StructField("created_at", StringType(), nullable=False),
    ]
)

SILVER_COLUMNS = [
    "kafka_key",
    "topic",
    "partition",
    "offset",
    "kafka_timestamp",
    "product_id",
    "user_id",
    "score",
    "text",
    "source",
    "review_id",
    "created_at",
    "sentiment",
    "text_length",
    "word_count",
    "has_negative_keywords",
    "has_positive_keywords",
]

AMAZON_REQUIRED_COLUMNS = ["Id", "ProductId", "UserId", "Score", "Text", "Time"]


def select_kafka_review_events(raw_reviews: Any) -> Any:
    return raw_reviews.select(
        col("key").cast("string").alias("kafka_key"),
        col("value").cast("string").alias("json_value"),
        col("topic"),
        col("partition"),
        col("offset"),
        col("timestamp").alias("kafka_timestamp"),
    )


def parse_review_events(review_events: Any) -> Any:
    return review_events.select(
        "kafka_key",
        "topic",
        "partition",
        "offset",
        "kafka_timestamp",
        from_json(col("json_value"), REVIEW_EVENT_SCHEMA).alias("review"),
    ).select(
        "kafka_key",
        "topic",
        "partition",
        "offset",
        "kafka_timestamp",
        col("review.product_id").alias("product_id"),
        col("review.user_id").alias("user_id"),
        col("review.score").alias("score"),
        col("review.text").alias("text"),
        col("review.source").alias("source"),
        col("review.review_id").alias("review_id"),
        to_timestamp(col("review.created_at")).alias("created_at"),
    )
