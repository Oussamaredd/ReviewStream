from spark.paths import (
    amazon_reviews_csv_path,
    bronze_amazon_reviews_raw_path,
    bronze_reviews_raw_path,
    checkpoint_path,
    hdfs_base_path,
    hdfs_default_fs,
    silver_reviews_enriched_path,
    spark_read_path,
)
from spark.review_schema import AMAZON_REQUIRED_COLUMNS, SILVER_COLUMNS
from spark.sentiment import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS, classify_score, has_any_keyword
from spark.settings import SparkSettings


def test_score_classification_matches_streaming_rule() -> None:
    assert classify_score(5) == "positive"
    assert classify_score(4) == "positive"
    assert classify_score(3) == "neutral"
    assert classify_score(2) == "negative"
    assert classify_score(1) == "negative"


def test_keyword_matching_uses_word_boundaries() -> None:
    assert has_any_keyword("This is excellent and fresh", POSITIVE_KEYWORDS)
    assert has_any_keyword("The product was stale and disgusting", NEGATIVE_KEYWORDS)
    assert not has_any_keyword("The greatness was debatable", POSITIVE_KEYWORDS)


def test_hdfs_paths_are_configurable(monkeypatch) -> None:
    monkeypatch.setenv("HDFS_BASE_PATH", "hdfs://example:9000/custom")
    monkeypatch.setenv("AMAZON_REVIEWS_CSV", "hdfs://example:9000/data/Reviews.csv")

    assert hdfs_base_path() == "hdfs://example:9000/custom"
    assert hdfs_default_fs() == "hdfs://example:9000"
    assert amazon_reviews_csv_path() == "hdfs://example:9000/data/Reviews.csv"
    assert bronze_reviews_raw_path() == "hdfs://example:9000/custom/bronze/reviews_raw"
    assert (
        bronze_amazon_reviews_raw_path() == "hdfs://example:9000/custom/bronze/amazon_reviews_raw"
    )
    assert silver_reviews_enriched_path() == "hdfs://example:9000/custom/silver/reviews_enriched"
    assert (
        checkpoint_path("silver_reviews") == "hdfs://example:9000/custom/checkpoints/silver_reviews"
    )
    assert spark_read_path("hdfs://example:9000/data/Reviews.csv") == (
        "hdfs://example:9000/data/Reviews.csv"
    )
    assert spark_read_path("data/Reviews.csv").startswith("file://")


def test_hdfs_paths_default_to_host_docker_port(monkeypatch) -> None:
    monkeypatch.delenv("HDFS_BASE_PATH", raising=False)
    monkeypatch.delenv("HDFS_DEFAULT_FS", raising=False)

    assert hdfs_base_path() == "hdfs://localhost:9000/reviewstream"
    assert hdfs_default_fs() == "hdfs://localhost:9000"


def test_spark_settings_use_local_demo_defaults(monkeypatch) -> None:
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
    monkeypatch.delenv("KAFKA_TOPIC", raising=False)
    monkeypatch.delenv("SPARK_KAFKA_FAIL_ON_DATA_LOSS", raising=False)
    monkeypatch.delenv("SPARK_SQL_SHUFFLE_PARTITIONS", raising=False)
    monkeypatch.delenv("SPARK_STREAM_TRIGGER_SECONDS", raising=False)
    monkeypatch.delenv("HDFS_CLIENT_USE_DATANODE_HOSTNAME", raising=False)

    defaults = SparkSettings()

    assert defaults.kafka_bootstrap_servers == "localhost:9092"
    assert defaults.kafka_topic == "reviews"
    assert defaults.kafka_fail_on_data_loss == "false"
    assert defaults.shuffle_partitions == 1
    assert defaults.stream_trigger_seconds == 30
    assert defaults.hdfs_client_use_datanode_hostname == "true"

    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    monkeypatch.setenv("KAFKA_TOPIC", "custom-reviews")
    monkeypatch.setenv("SPARK_KAFKA_FAIL_ON_DATA_LOSS", "true")
    monkeypatch.setenv("SPARK_SQL_SHUFFLE_PARTITIONS", "2")
    monkeypatch.setenv("SPARK_STREAM_TRIGGER_SECONDS", "15")
    monkeypatch.setenv("HDFS_CLIENT_USE_DATANODE_HOSTNAME", "true")

    configured = SparkSettings()

    assert configured.kafka_bootstrap_servers == "kafka:29092"
    assert configured.kafka_topic == "custom-reviews"
    assert configured.kafka_fail_on_data_loss == "true"
    assert configured.shuffle_partitions == 2
    assert configured.stream_trigger_seconds == 15
    assert configured.hdfs_client_use_datanode_hostname == "true"


def test_shared_schema_columns_include_text_analytics() -> None:
    assert AMAZON_REQUIRED_COLUMNS == ["Id", "ProductId", "UserId", "Score", "Text", "Time"]
    assert SILVER_COLUMNS[-4:] == [
        "text_length",
        "word_count",
        "has_negative_keywords",
        "has_positive_keywords",
    ]
