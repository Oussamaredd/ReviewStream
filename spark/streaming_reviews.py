import os

from dotenv import load_dotenv
from pyspark.sql import SparkSession

from spark.review_schema import parse_review_events, select_kafka_review_events

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "reviews")


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

    review_events = select_kafka_review_events(raw_reviews)
    parsed_reviews = parse_review_events(review_events)

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
