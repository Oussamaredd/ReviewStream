# ReviewStream

ReviewStream is a local development and demo data pipeline for product reviews. A FastAPI
backend receives review events, publishes them to Kafka, Spark Structured Streaming stores
bronze and silver datasets in HDFS, Hive exposes the silver Parquet data, and the API serves
Hive-backed analytics endpoints.

This project is intentionally unauthenticated and intended for local development only. Do not
expose these services or API endpoints directly to the public internet.

## Architecture

```text
curl/client
  -> FastAPI POST /reviews
  -> Kafka topic reviews
  -> Spark Structured Streaming
  -> HDFS bronze JSON: /reviewstream/bronze/reviews_raw
  -> HDFS silver Parquet: /reviewstream/silver/reviews_enriched
  -> Hive external table: reviewstream.reviews_enriched
  -> FastAPI analytics endpoints
  -> future dashboard
```

More detail is available in [docs/architecture.md](docs/architecture.md).

## Services And Ports

| Service | Container | Port |
| --- | --- | --- |
| FastAPI backend | local process | `8000` |
| Kafka | `reviewstream-kafka` | `9092` |
| Kafka UI | `reviewstream-kafka-ui` | `8080` |
| HDFS NameNode web UI | `reviewstream-namenode` | `9870` |
| HDFS NameNode RPC | `reviewstream-namenode` | `9000` |
| HDFS DataNode UI/data | `reviewstream-datanode` | `9864`, `9866` |
| Hive Metastore | `reviewstream-hive-metastore` | `9083` |
| HiveServer2 | `reviewstream-hive-server` | `10000`, `10002` |
| PostgreSQL metastore DB | `reviewstream-hive-metastore-postgresql` | internal `5432` |
| Zookeeper | `reviewstream-zookeeper` | internal `2181` |

## Local Setup

Use Python 3.12 for local development and CI parity.

```bash
make setup
make dev-install
cp .env.example .env
```

The default `.env.example` values are local Docker defaults and should work for the standard
Compose stack.

## Run Docker Services

```bash
make docker-up
make kafka-topic
make hdfs-wait
make hdfs-init
make hive-metastore-init
make hive-wait
make hive-init
```

Useful inspection commands:

```bash
make docker-logs
make hdfs-ls
make hive-tables
make hive-query
```

Stop the stack with:

```bash
make docker-down
```

## Start The API

Run the API in a separate terminal:

```bash
make api
```

Health check:

```bash
curl http://localhost:8000/health
```

## Submit Reviews

Use the Makefile sample:

```bash
make test-review
```

Or submit JSON directly:

```bash
curl -X POST http://localhost:8000/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "P001",
    "user_id": "client1",
    "score": 5,
    "text": "Great product",
    "source": "web"
  }'
```

## Run Spark Storage Job

Run the storage stream in a separate terminal while Kafka, HDFS, and Hive services are up:

```bash
make spark-storage
```

This job reads Kafka topic `reviews`, writes raw Kafka records as bronze JSON, enriches reviews
with sentiment, and writes silver Parquet records for Hive.

You can also run the console-only Spark examples:

```bash
make spark-stream
make spark-analytics
make spark-read-silver
```

## Initialize And Query Hive

Initialize the metastore schema and create the external table:

```bash
make hive-metastore-init
make hive-wait
make hive-init
```

Inspect the external table:

```bash
make hive-tables
make hive-query
make hive-shell
```

Hive exposes:

```text
database: reviewstream
table: reviews_enriched
path: /reviewstream/silver/reviews_enriched
```

## Analytics API

Analytics endpoints query Hive through the backend. If Hive is unavailable, the API returns a
safe `503` response with `{"detail": "Analytics service is unavailable"}`.

```bash
curl http://localhost:8000/analytics/summary
curl http://localhost:8000/analytics/sentiment
curl http://localhost:8000/analytics/products
curl http://localhost:8000/analytics/products?limit=5
curl http://localhost:8000/analytics
```

Current endpoints are documented in [docs/api.md](docs/api.md).

## Tests And Checks

Tests mock Hive access, so Docker, Kafka, HDFS, Spark, and Hive do not need to be running.

```bash
make format
make check
pytest
mypy backend spark
docker compose config
```

CI runs compile, Ruff, Black check, mypy, pytest, and Docker Compose config validation on push
and pull request.
