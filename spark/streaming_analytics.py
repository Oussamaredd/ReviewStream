import os

from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, col, count, from_json, round, to_timestamp, when
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "reviews")


review_schema = StructType(
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


def read_reviews_from_kafka(spark: SparkSession):
    raw_reviews = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .load()
    )

    return raw_reviews.select(
        col("key").cast("string").alias("kafka_key"),
        col("value").cast("string").alias("json_value"),
        col("topic"),
        col("partition"),
        col("offset"),
        col("timestamp").alias("kafka_timestamp"),
    )


def parse_reviews(review_events):
    return review_events.select(
        "kafka_key",
        "topic",
        "partition",
        "offset",
        "kafka_timestamp",
        from_json(col("json_value"), review_schema).alias("review"),
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


def add_sentiment(reviews):
    return reviews.withColumn(
        "sentiment",
        when(col("score") >= 4, "positive")
        .when(col("score") == 3, "neutral")
        .otherwise("negative"),
    )


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamAnalytics")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    review_events = read_reviews_from_kafka(spark)
    reviews = add_sentiment(parse_reviews(review_events))

    sentiment_counts = reviews.groupBy("sentiment").agg(count("*").alias("review_count"))

    product_scores = (
        reviews.groupBy("product_id")
        .agg(
            count("*").alias("review_count"),
            round(avg("score"), 2).alias("average_score"),
        )
        .orderBy(col("review_count").desc())
    )

    (
        sentiment_counts.writeStream.queryName("reviews_by_sentiment")
        .format("console")
        .outputMode("complete")
        .option("truncate", "false")
        .start()
    )

    (
        product_scores.writeStream.queryName("product_score_summary")
        .format("console")
        .outputMode("complete")
        .option("truncate", "false")
        .start()
    )

    print(f"Spark analytics is listening to Kafka topic: {KAFKA_TOPIC}")
    print("Submit reviews with: make test-review")

    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
