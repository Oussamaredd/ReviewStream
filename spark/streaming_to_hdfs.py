import os

from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, when
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "reviews")
HDFS_BASE_PATH = os.getenv("HDFS_BASE_PATH", "hdfs://namenode:9000/reviewstream")


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

    bronze_reviews = raw_reviews.select(
        col("key").cast("string").alias("kafka_key"),
        col("value").cast("string").alias("json_value"),
        col("topic"),
        col("partition"),
        col("offset"),
        col("timestamp").alias("kafka_timestamp"),
    )

    parsed_reviews = bronze_reviews.select(
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

    silver_reviews = parsed_reviews.withColumn(
        "sentiment",
        when(col("score") >= 4, "positive")
        .when(col("score") == 3, "neutral")
        .otherwise("negative"),
    )

    bronze_query = (
        bronze_reviews.writeStream.queryName("bronze_reviews_raw_to_hdfs")
        .format("json")
        .outputMode("append")
        .option("path", f"{HDFS_BASE_PATH}/bronze/reviews_raw")
        .option("checkpointLocation", f"{HDFS_BASE_PATH}/checkpoints/bronze_reviews_raw")
        .start()
    )

    silver_query = (
        silver_reviews.writeStream.queryName("silver_reviews_enriched_to_hdfs")
        .format("parquet")
        .outputMode("append")
        .option("path", f"{HDFS_BASE_PATH}/silver/reviews_enriched")
        .option("checkpointLocation", f"{HDFS_BASE_PATH}/checkpoints/silver_reviews_enriched")
        .start()
    )

    print("Spark is writing review streams to HDFS")
    print(f"Bronze path: {HDFS_BASE_PATH}/bronze/reviews_raw")
    print(f"Silver path: {HDFS_BASE_PATH}/silver/reviews_enriched")
    print("Submit reviews with: make test-review")

    spark.streams.awaitAnyTermination()

    bronze_query.stop()
    silver_query.stop()


if __name__ == "__main__":
    main()
