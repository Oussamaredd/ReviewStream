from pyspark.sql import SparkSession

from spark.review_schema import parse_review_events, select_kafka_review_events
from spark.settings import settings


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamKafkaConsumer")
        .config("spark.sql.shuffle.partitions", str(settings.shuffle_partitions))
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    raw_reviews = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", settings.kafka_bootstrap_servers)
        .option("subscribe", settings.kafka_topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", settings.kafka_fail_on_data_loss)
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

    print(f"Spark is listening to Kafka topic: {settings.kafka_topic}")
    print("Submit a review with: make test-review")

    query.awaitTermination()


if __name__ == "__main__":
    main()
