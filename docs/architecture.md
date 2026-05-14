# Architecture

ReviewStream keeps the original FastAPI, Kafka, Spark, HDFS, and Hive architecture while adding a
historical batch lane and a dashboard-ready analytics API.

The project is unauthenticated and intended for local demos only.

## Data Flow

```text
Historical batch:
  Amazon Reviews.csv
    -> spark/batch_ingest_amazon_reviews.py
    -> HDFS /reviewstream/bronze/amazon_reviews_raw
    -> HDFS /reviewstream/silver/reviews_enriched

Live streaming:
  Vue dashboard or curl
    -> FastAPI POST /reviews
    -> Kafka topic reviews
    -> spark/streaming_to_hdfs.py
    -> HDFS /reviewstream/bronze/reviews_raw
    -> HDFS /reviewstream/silver/reviews_enriched

Serving:
  Hive external table reviewstream.reviews_enriched
    -> FastAPI analytics endpoints
    -> Vue dashboard polling GET /analytics/dashboard
```

## Silver Schema

Both batch and streaming jobs write the same normalized silver columns:

```text
kafka_key
topic
partition
offset
kafka_timestamp
product_id
user_id
score
text
source
review_id
created_at
sentiment
text_length
word_count
has_negative_keywords
has_positive_keywords
```

Kafka metadata is `NULL` for historical Amazon CSV rows. Historical rows use
`source = 'amazon_csv'`; live dashboard/API rows default to `source = 'web'`.

## Enrichment

Shared Spark helpers keep batch and streaming logic aligned:

- `spark/review_schema.py` defines event schema, silver column order, and Kafka parsing.
- `spark/sentiment.py` defines score sentiment and lightweight text keyword fields.
- `spark/paths.py` centralizes configurable HDFS and CSV paths.

Sentiment rule:

```text
score >= 4 -> positive
score == 3 -> neutral
otherwise -> negative
```

Keyword fields use simple word-boundary matching against small positive and negative keyword
lists. This is intentionally lightweight text analytics, not full NLP.

## Storage

Bronze:

- Live raw Kafka JSON: `/reviewstream/bronze/reviews_raw`
- Cleaned Amazon CSV rows: `/reviewstream/bronze/amazon_reviews_raw`

Silver:

- Enriched Parquet: `/reviewstream/silver/reviews_enriched`

Hive:

- Database: `reviewstream`
- Table: `reviews_enriched`
- Type: external Parquet table
- Location: `/reviewstream/silver/reviews_enriched`

## Serving

FastAPI exposes fixed backend-controlled analytics queries. Numeric query parameters are validated
with FastAPI `Query` constraints before being formatted into SQL. Hive/PyHive failures are logged
internally and returned as safe `503` responses.

The dashboard polls `GET /analytics/dashboard` every few seconds and submits live reviews through
`POST /reviews`.
