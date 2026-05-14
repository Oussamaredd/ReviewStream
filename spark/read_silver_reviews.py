from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

from spark.paths import silver_reviews_enriched_path

load_dotenv()


def main() -> None:
    spark = (
        SparkSession.builder.appName("ReviewStreamReadSilver")
        .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000")
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    silver_path = silver_reviews_enriched_path()

    reviews = spark.read.parquet(silver_path)

    print(f"Reading silver reviews from: {silver_path}")
    print(f"Total rows: {reviews.count()}")

    reviews.select(
        "product_id",
        "user_id",
        "score",
        "sentiment",
        "source",
        "text_length",
        "word_count",
        "has_negative_keywords",
        "has_positive_keywords",
        "text",
        "review_id",
        "created_at",
        "offset",
    ).orderBy(col("offset").desc()).show(20, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
