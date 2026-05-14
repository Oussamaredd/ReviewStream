CREATE DATABASE IF NOT EXISTS reviewstream;

USE reviewstream;

DROP TABLE IF EXISTS reviews_enriched;

CREATE EXTERNAL TABLE reviews_enriched (
  kafka_key STRING,
  topic STRING,
  `partition` INT,
  `offset` BIGINT,
  kafka_timestamp TIMESTAMP,
  product_id STRING,
  user_id STRING,
  score INT,
  text STRING,
  source STRING,
  review_id STRING,
  created_at TIMESTAMP,
  sentiment STRING
)
STORED AS PARQUET
LOCATION '/reviewstream/silver/reviews_enriched';

SELECT COUNT(*) AS total_reviews FROM reviews_enriched;

SELECT sentiment, COUNT(*) AS review_count
FROM reviews_enriched
GROUP BY sentiment;

SELECT product_id, COUNT(*) AS review_count, AVG(score) AS average_score
FROM reviews_enriched
GROUP BY product_id;
