from pyspark.sql import SparkSession

from spark.paths import (
    bronze_reviews_raw_path,
    checkpoint_path,
    hdfs_default_fs,
    silver_reviews_enriched_path,
)
from spark.review_schema import SILVER_COLUMNS, parse_review_events, select_kafka_review_events
from spark.sentiment import enrich_reviews
from spark.settings import settings


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamHDFSWriter")
        .config("spark.sql.shuffle.partitions", str(settings.shuffle_partitions))
        .config("spark.hadoop.fs.defaultFS", hdfs_default_fs())
        .config("spark.hadoop.dfs.replication", "1")
        .config(
            "spark.hadoop.dfs.client.use.datanode.hostname",
            settings.hdfs_client_use_datanode_hostname,
        )
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

    bronze_reviews = select_kafka_review_events(raw_reviews)
    parsed_reviews = parse_review_events(bronze_reviews)
    silver_reviews = enrich_reviews(parsed_reviews).select(*SILVER_COLUMNS)

    bronze_query = (
        bronze_reviews.writeStream.queryName("bronze_reviews_raw_to_hdfs")
        .format("json")
        .outputMode("append")
        .option("path", bronze_reviews_raw_path())
        .option("checkpointLocation", checkpoint_path("bronze_reviews_raw"))
        .trigger(processingTime=f"{settings.stream_trigger_seconds} seconds")
        .start()
    )

    silver_query = (
        silver_reviews.writeStream.queryName("silver_reviews_enriched_to_hdfs")
        .format("parquet")
        .outputMode("append")
        .option("path", silver_reviews_enriched_path())
        .option("checkpointLocation", checkpoint_path("silver_reviews_enriched"))
        .trigger(processingTime=f"{settings.stream_trigger_seconds} seconds")
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
