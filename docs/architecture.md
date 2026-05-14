# Architecture

ReviewStream is a local/demo data pipeline for product reviews. It is designed to show the
movement from an API event to streaming storage and then back to a queryable analytics API.

The services are unauthenticated and use local development defaults. Keep them on trusted local
networks only.

## End-To-End Flow

```text
1. Client sends a review
   POST /reviews -> FastAPI

2. Backend validates the request
   Pydantic ReviewIn -> ReviewEvent with review_id and created_at

3. Backend publishes the event
   Kafka topic: reviews

4. Spark Structured Streaming consumes Kafka
   key/value/timestamp/partition/offset are read from Kafka

5. Spark writes bronze data
   HDFS JSON path: /reviewstream/bronze/reviews_raw

6. Spark writes silver data
   parsed review fields plus sentiment
   HDFS Parquet path: /reviewstream/silver/reviews_enriched

7. Hive exposes silver data
   database: reviewstream
   external table: reviews_enriched
   location: /reviewstream/silver/reviews_enriched

8. FastAPI analytics endpoints query Hive
   GET /analytics/summary
   GET /analytics/sentiment
   GET /analytics/products
   GET /analytics

9. Future dashboard reads the API
   frontend/dashboard work should consume the existing unauthenticated local API
```

## Components

FastAPI backend:

- `POST /reviews` accepts validated review payloads.
- Kafka producer sends JSON events to topic `reviews`.
- Analytics routes query Hive with fixed backend-controlled SQL.
- Analytics failures return a safe `503` response instead of leaking PyHive or Thrift details.

Kafka:

- Topic: `reviews`.
- Local bootstrap server: `localhost:9092`.
- Internal Docker bootstrap server: `kafka:29092`.
- Kafka UI is available at `http://localhost:8080`.

Spark:

- `spark/streaming_to_hdfs.py` is the storage job for bronze and silver data.
- `spark/streaming_reviews.py` is a console consumer example.
- `spark/streaming_analytics.py` is a console streaming aggregation example.
- `spark/read_silver_reviews.py` reads silver Parquet output for inspection.

HDFS:

- Base path defaults to `hdfs://namenode:9000/reviewstream`.
- Bronze raw Kafka JSON goes to `/reviewstream/bronze/reviews_raw`.
- Silver enriched Parquet goes to `/reviewstream/silver/reviews_enriched`.
- Checkpoints go under `/reviewstream/checkpoints`.

Hive:

- Metastore uses a PostgreSQL metastore DB container.
- HiveServer2 listens on `localhost:10000`.
- `hive/init.sql` creates the `reviewstream.reviews_enriched` external table.

Analytics API:

- `GET /analytics/summary` returns total count, average score, and first/last review times.
- `GET /analytics/sentiment` returns counts grouped by sentiment.
- `GET /analytics/products` returns product score aggregates with `limit` constrained to 1-100.
- `GET /analytics` returns the combined summary, sentiment, and default top products payload.

## Data Shape

Incoming review payload:

```json
{
  "product_id": "P001",
  "user_id": "client1",
  "score": 5,
  "text": "Great product",
  "source": "web"
}
```

The backend adds:

```text
review_id: UUID string
created_at: UTC ISO timestamp
```

The silver Spark job adds:

```text
sentiment: positive when score >= 4, neutral when score == 3, otherwise negative
```
