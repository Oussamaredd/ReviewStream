import os

from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, col, count, round

from spark.review_schema import parse_review_events, select_kafka_review_events
from spark.sentiment import add_sentiment

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "reviews")


def read_reviews_from_kafka(spark: SparkSession):
    raw_reviews = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .load()
    )

    return select_kafka_review_events(raw_reviews)


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamAnalytics")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    review_events = read_reviews_from_kafka(spark)
    reviews = add_sentiment(parse_review_events(review_events))

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
