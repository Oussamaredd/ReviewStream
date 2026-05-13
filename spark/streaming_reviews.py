import os

from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
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


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamKafkaConsumer")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    raw_reviews = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .load()
    )

    review_events = raw_reviews.select(
        col("key").cast("string").alias("kafka_key"),
        col("value").cast("string").alias("json_value"),
        col("topic"),
        col("partition"),
        col("offset"),
        col("timestamp").alias("kafka_timestamp"),
    )

    parsed_reviews = review_events.select(
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

    query = (
        parsed_reviews.writeStream.queryName("live_reviews_console")
        .format("console")
        .outputMode("append")
        .option("truncate", "false")
        .option("numRows", 20)
        .start()
    )

    print(f"Spark is listening to Kafka topic: {KAFKA_TOPIC}")
    print("Submit a review with: make test-review")

    query.awaitTermination()


if __name__ == "__main__":
    main()
