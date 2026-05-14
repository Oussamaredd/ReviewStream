import os

from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

load_dotenv()

HDFS_BASE_PATH = os.getenv("HDFS_BASE_PATH", "hdfs://namenode:9000/reviewstream")


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamReadSilver")
        .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000")
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    silver_path = f"{HDFS_BASE_PATH}/silver/reviews_enriched"

    reviews = spark.read.parquet(silver_path)

    print(f"Reading silver reviews from: {silver_path}")
    print(f"Total rows: {reviews.count()}")

    reviews.select(
        "product_id",
        "user_id",
        "score",
        "sentiment",
        "text",
        "review_id",
        "created_at",
        "offset",
    ).orderBy(col("offset").desc()).show(20, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
