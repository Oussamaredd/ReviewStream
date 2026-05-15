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
  Vue Products page or curl
    -> FastAPI POST /products/{product_id}/reviews or POST /reviews
    -> Kafka topic reviews
    -> spark/streaming_to_hdfs.py
    -> HDFS /reviewstream/bronze/reviews_raw
    -> HDFS /reviewstream/silver/reviews_enriched

Serving:
  Hive external table reviewstream.reviews_enriched
    -> FastAPI analytics endpoints
    -> Vue Analytics page polling GET /analytics/dashboard
```

## Application Surface

The Vue app is split into two primary pages:

- Products page: loads the static product catalog from `GET /products` and submits reviews through
  `POST /products/{product_id}/reviews`.
- Analytics page: polls `GET /analytics/dashboard` for summary metrics, product tables,
  distributions, keyword counts, and review/opinion text.

The product catalog is a backend static module, not a database. Catalog endpoints stay available
when Kafka, Spark, HDFS, or Hive are offline. The client-facing product review endpoint validates
the catalog product, accepts only `score` and `text`, attaches `product_id`, a demo `user_id`, and
`source = web`, then publishes the same event schema used by `POST /reviews`.

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

Only `GET /analytics/dashboard` has a process-local in-memory fallback cache. Fresh successful
dashboard responses are normalized, tagged with `status`, `stale`, and `generated_at`, and stored.
If Hive later fails, the endpoint returns the cached snapshot with `status = cached`, `stale = true`,
and a warning. Strict callers can request
`/analytics/dashboard?prefer_cache=false&allow_sample=false` to receive `503` when Hive fails
before any successful dashboard.

Default dashboard requests use `prefer_cache=true&allow_sample=true`: they return the process cache
immediately when it exists. If no process cache exists, they return a sample dashboard computed
from committed `data/sample_reviews.csv` and start a throttled background Hive refresh. This keeps
the Analytics page visible while HiveServer2 or MapReduce jobs warm up.

Empty Hive tables are valid. The dashboard summary defaults to zero/null values and list sections
default to empty lists so the frontend can render cold demos without null-breaking payloads.

Individual analytics endpoints such as `/analytics/sentiment` and `/analytics/opinions` still
return `503` on Hive failures.
