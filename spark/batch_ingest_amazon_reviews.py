from typing import Any

from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_unixtime, length, lit, trim

from spark.paths import (
    amazon_reviews_csv_path,
    bronze_amazon_reviews_raw_path,
    hdfs_default_fs,
    silver_reviews_enriched_path,
    spark_read_path,
)
from spark.review_schema import AMAZON_REQUIRED_COLUMNS, SILVER_COLUMNS
from spark.sentiment import enrich_reviews
from spark.settings import settings

load_dotenv()


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("ReviewStreamAmazonReviewsBatchIngest")
        .config("spark.sql.shuffle.partitions", str(settings.shuffle_partitions))
        .config("spark.hadoop.fs.defaultFS", hdfs_default_fs())
        .config("spark.hadoop.dfs.replication", "1")
        .config(
            "spark.hadoop.dfs.client.use.datanode.hostname",
            settings.hdfs_client_use_datanode_hostname,
        )
        .getOrCreate()
    )


def read_amazon_reviews_csv(spark: SparkSession, input_path: str) -> Any:
    return (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .option("multiLine", "true")
        .option("escape", '"')
        .csv(input_path)
    )


def clean_amazon_reviews(raw_reviews: Any) -> Any:
    cleaned = raw_reviews.dropna(subset=AMAZON_REQUIRED_COLUMNS)

    for column_name in ["ProductId", "UserId", "Text"]:
        cleaned = cleaned.filter(length(trim(col(column_name).cast("string"))) > 0)

    return cleaned.filter(
        (col("Id").cast("long").isNotNull())
        & (col("Score").cast("int").between(1, 5))
        & (col("Time").cast("long").isNotNull())
    )


def normalize_amazon_reviews(cleaned_reviews: Any) -> Any:
    normalized = cleaned_reviews.select(
        lit(None).cast("string").alias("kafka_key"),
        lit(None).cast("string").alias("topic"),
        lit(None).cast("int").alias("partition"),
        lit(None).cast("long").alias("offset"),
        lit(None).cast("timestamp").alias("kafka_timestamp"),
        col("ProductId").cast("string").alias("product_id"),
        col("UserId").cast("string").alias("user_id"),
        col("Score").cast("int").alias("score"),
        col("Text").cast("string").alias("text"),
        lit("amazon_csv").alias("source"),
        col("Id").cast("string").alias("review_id"),
        from_unixtime(col("Time").cast("long")).cast("timestamp").alias("created_at"),
    )

    return enrich_reviews(normalized).select(*SILVER_COLUMNS)


def main() -> None:
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    input_path = amazon_reviews_csv_path()
    resolved_input_path = spark_read_path(input_path)
    bronze_path = bronze_amazon_reviews_raw_path()
    silver_path = silver_reviews_enriched_path()

    raw_reviews = read_amazon_reviews_csv(spark, resolved_input_path)
    cleaned_reviews = clean_amazon_reviews(raw_reviews)
    enriched_reviews = normalize_amazon_reviews(cleaned_reviews)

    raw_row_count = raw_reviews.count()
    cleaned_row_count = cleaned_reviews.count()
    written_row_count = enriched_reviews.count()

    cleaned_reviews.write.mode("append").json(bronze_path)
    enriched_reviews.write.mode("append").parquet(silver_path)

    print("Amazon Reviews CSV batch ingestion complete")
    print(f"Input path: {input_path}")
    if resolved_input_path != input_path:
        print(f"Spark read path: {resolved_input_path}")
    print(f"Bronze path: {bronze_path}")
    print(f"Silver path: {silver_path}")
    print(f"Raw row count: {raw_row_count}")
    print(f"Cleaned row count: {cleaned_row_count}")
    print(f"Written row count: {written_row_count}")

    spark.stop()


if __name__ == "__main__":
    main()
