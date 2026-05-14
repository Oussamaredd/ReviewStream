# AGENTS.md

Context for future coding agents working in this repository.

## Project Context

ReviewStream is a local development/demo data pipeline for product reviews:

```text
Amazon Reviews.csv -> Spark batch -> HDFS bronze/silver -> Hive -> analytics API -> dashboard
FastAPI -> Kafka -> Spark Structured Streaming -> HDFS bronze/silver -> Hive -> analytics API
```

The frontend/dashboard work exists separately on `origin/frontend-feature`. Do not delete,
rewrite, or modify that branch unless the user explicitly asks.

## Main Commands

```bash
make setup
make dev-install
make docker-up
make kafka-topic
make hdfs-wait
make hdfs-init
make hive-metastore-init
make hive-wait
make hive-init
make batch-amazon
make api
make spark-storage
make dashboard-ready-check
make format
make check
pytest
mypy backend spark
docker compose config
```

## Architecture Expectations

- `POST /reviews` validates review payloads and publishes JSON messages to Kafka topic `reviews`.
- Spark consumes Kafka and writes bronze JSON to `/reviewstream/bronze/reviews_raw`.
- `spark/batch_ingest_amazon_reviews.py` ingests Amazon `Reviews.csv` into
  `/reviewstream/bronze/amazon_reviews_raw` and appends silver Parquet rows.
- Spark writes enriched silver Parquet to `/reviewstream/silver/reviews_enriched`.
- Hive exposes silver data as external table `reviewstream.reviews_enriched`.
- FastAPI analytics endpoints query Hive with fixed backend-controlled SQL.
- The Vue dashboard submits live reviews and polls `GET /analytics/dashboard`.
- Do not remove Kafka, Spark, HDFS, or Hive functionality while hardening the backend.

## Security And Scope

- Keep authentication out of scope unless the user explicitly requests it.
- The API and Compose services are unauthenticated local/demo services.
- Do not expose this project to the public internet as-is.
- Do not commit secrets, tokens, credentials, or local private data.
- Do not commit large datasets such as `data/Reviews.csv`.
- Keep `.env.example` limited to safe local defaults.

## Development Guidelines

- Prefer small, focused commits.
- Preserve existing Makefile behavior, especially `make format`, `make check`, `make hive-wait`,
  and `make hive-tables`.
- Run formatting, checks, tests, and type checks before committing:

```bash
make format
make check
pytest
mypy backend spark
docker compose config
```

- Tests should mock Hive/Kafka/Spark/HDFS when validating backend route behavior.
- Avoid raw SQL from users. Keep analytics queries fixed in backend code and validate any query
  parameters with FastAPI constraints.
