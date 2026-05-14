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
  sentiment STRING,
  text_length INT,
  word_count INT,
  has_negative_keywords BOOLEAN,
  has_positive_keywords BOOLEAN
)
STORED AS PARQUET
LOCATION '/reviewstream/silver/reviews_enriched';

SELECT COUNT(*) AS total_reviews
FROM reviews_enriched;

SELECT sentiment, COUNT(*) AS review_count
FROM reviews_enriched
GROUP BY sentiment
ORDER BY sentiment;

SELECT score, COUNT(*) AS review_count
FROM reviews_enriched
GROUP BY score
ORDER BY score;

SELECT source, COUNT(*) AS review_count
FROM reviews_enriched
GROUP BY source
ORDER BY review_count DESC;

SELECT product_id, COUNT(*) AS review_count, AVG(score) AS average_score
FROM reviews_enriched
GROUP BY product_id
HAVING COUNT(*) >= 5
ORDER BY average_score DESC, review_count DESC
LIMIT 10;

SELECT product_id, COUNT(*) AS review_count, AVG(score) AS average_score
FROM reviews_enriched
GROUP BY product_id
HAVING COUNT(*) >= 5
ORDER BY average_score ASC, review_count DESC
LIMIT 10;

SELECT
  product_id,
  SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_review_count,
  COUNT(*) AS review_count,
  AVG(score) AS average_score
FROM reviews_enriched
GROUP BY product_id
HAVING COUNT(*) >= 3 AND SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) > 0
ORDER BY negative_review_count DESC, average_score ASC
LIMIT 10;
