from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, col, count, round

from spark.review_schema import parse_review_events, select_kafka_review_events
from spark.sentiment import add_sentiment
from spark.settings import settings


def read_reviews_from_kafka(spark: SparkSession):
    raw_reviews = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", settings.kafka_bootstrap_servers)
        .option("subscribe", settings.kafka_topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", settings.kafka_fail_on_data_loss)
        .load()
    )

    return select_kafka_review_events(raw_reviews)


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamAnalytics")
        .config("spark.sql.shuffle.partitions", str(settings.shuffle_partitions))
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

    print(f"Spark analytics is listening to Kafka topic: {settings.kafka_topic}")
    print("Submit reviews with: make test-review")

    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
