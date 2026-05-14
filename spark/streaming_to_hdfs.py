import os

from dotenv import load_dotenv
from pyspark.sql import SparkSession

from spark.paths import bronze_reviews_raw_path, checkpoint_path, silver_reviews_enriched_path
from spark.review_schema import SILVER_COLUMNS, parse_review_events, select_kafka_review_events
from spark.sentiment import enrich_reviews

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "reviews")


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamHDFSWriter")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000")
        .config("spark.hadoop.dfs.replication", "1")
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
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

    bronze_reviews = select_kafka_review_events(raw_reviews)
    parsed_reviews = parse_review_events(bronze_reviews)
    silver_reviews = enrich_reviews(parsed_reviews).select(*SILVER_COLUMNS)

    bronze_query = (
        bronze_reviews.writeStream.queryName("bronze_reviews_raw_to_hdfs")
        .format("json")
        .outputMode("append")
        .option("path", bronze_reviews_raw_path())
        .option("checkpointLocation", checkpoint_path("bronze_reviews_raw"))
        .start()
    )

    silver_query = (
        silver_reviews.writeStream.queryName("silver_reviews_enriched_to_hdfs")
        .format("parquet")
        .outputMode("append")
        .option("path", silver_reviews_enriched_path())
        .option("checkpointLocation", checkpoint_path("silver_reviews_enriched"))
        .start()
    )

    print("Spark is writing review streams to HDFS")
    print(f"Bronze path: {bronze_reviews_raw_path()}")
    print(f"Silver path: {silver_reviews_enriched_path()}")
    print("Submit reviews with: make test-review")

    spark.streams.awaitAnyTermination()

    bronze_query.stop()
    silver_query.stop()


if __name__ == "__main__":
    main()
