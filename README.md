# ReviewStream

ReviewStream is a local Big Data ecommerce review analytics project. It demonstrates two data
paths that land in the same Hive-backed analytics table:

- Historical batch ingestion from Amazon Fine Food Reviews `Reviews.csv`.
- Live review streaming from the Products page/API through Kafka and Spark.

The project is for local development and demos. The API, dashboard, and Docker services are
unauthenticated and must not be exposed directly to the public internet.

## Architecture

```text
Historical path:
  data/Reviews.csv
    -> Spark batch job
    -> HDFS bronze amazon_reviews_raw
    -> HDFS silver reviews_enriched
    -> Hive reviewstream.reviews_enriched
    -> FastAPI analytics
    -> Vue Analytics page

Live path:
  Vue Products page
    -> FastAPI POST /products/{product_id}/reviews
    -> Kafka topic reviews
    -> Spark Structured Streaming
    -> HDFS bronze reviews_raw
    -> HDFS silver reviews_enriched
    -> Hive reviewstream.reviews_enriched
    -> FastAPI analytics
    -> Vue Analytics page
```

Silver rows include normalized review fields, score-based sentiment, and lightweight text
analytics:

- `text_length`
- `word_count`
- `has_negative_keywords`
- `has_positive_keywords`

## Requirements

- Python 3.12
- Docker and Docker Compose
- Node.js 20+ for the dashboard
- Amazon Fine Food Reviews CSV when running historical ingestion

Do not commit `data/Reviews.csv`; `data/` is ignored except for `data/.gitkeep` and the tiny
fake `data/sample_reviews.csv`.

## Setup

```bash
make setup
make dev-install
cp .env.example .env
cd frontend && npm install && cd ..
```

Default local paths:

```text
AMAZON_REVIEWS_CSV=data/Reviews.csv
HDFS_BASE_PATH=hdfs://localhost:9000/reviewstream
```

Spark is not a long-running Docker container in this prototype. The Makefile runs Spark jobs from
the local Python virtual environment with low-CPU defaults: `local[1]`, `1g` driver memory, one
shuffle partition, and a 30-second streaming trigger.

Host-run Spark uses `hdfs://localhost:9000/reviewstream` by default because Docker service names
such as `namenode` only resolve inside the Compose network. HDFS advertises the DataNode as
`host.docker.internal` so Spark can write data from the host without joining the Docker network.
Spark Kafka streams also default `SPARK_KAFKA_FAIL_ON_DATA_LOSS=false` so local topic resets do not
break old HDFS checkpoints during demos.

## Application Pages

- Products: `http://localhost:5173/products`
- Analytics: `http://localhost:5173/analytics`

The Products page shows a static ecommerce-style catalog from `GET /products`. Users select a
product and submit only a score plus opinion text. The backend attaches `product_id`, a demo
`user_id`, and `source = web`, publishes the event to Kafka, and Spark/Hive analytics update after
the stream writes silver data.

The Analytics page polls `GET /analytics/dashboard` and shows summary metrics, distributions,
product tables, source counts, keyword counts, and recent review/opinion text.

The backend keeps route wiring, fixed Hive queries, dashboard fallback behavior, and review
queueing in separate modules. This keeps the school-demo prototype readable without changing the
pipeline or API contract.

## Dashboard States

- Fresh: Hive query succeeded and the API returned a new dashboard snapshot.
- Cached: Hive is unavailable, but the API returned the last successful dashboard snapshot.
- Sample: first paint tries Hive and uses committed `data/sample_reviews.csv` only if Hive is not
  ready. Set `DASHBOARD_BACKGROUND_REFRESH_ENABLED=true` when you want cached dashboard responses to
  trigger background Hive refreshes.
- Strict cold start: direct strict calls can still return `503` when Hive is unavailable and no
  cached dashboard exists yet.
- Empty: Hive is reachable but the table has no rows; the dashboard returns safe zero/empty values.

## Full Local Demo

Print the command order:

```bash
make demo-full
```

Quick demo with committed fake data:

```bash
make docker-up
make kafka-wait
make kafka-topic
make hdfs-wait
make hdfs-init
make hive-metastore-init
make hive-init
make seed-sample
```

Start these in separate terminals:

```bash
make api
make frontend-dev
```

Optional live streaming:

```bash
make spark-storage
```

Open:

```text
http://localhost:5173/products
http://localhost:5173/analytics
```

Check readiness:

```bash
make dashboard-ready-check
```

If review submission returns `503`, check Kafka from the API side:

```bash
make kafka-wait
make kafka-topic
make kafka-health
```

## Historical Batch Ingestion

Path A, quick sample data:

```bash
make seed-sample
```

Path B, full historical demo:

Download the Amazon Fine Food Reviews dataset from Kaggle:

```text
https://www.kaggle.com/datasets/snap/amazon-fine-food-reviews
```

Extract `Reviews.csv` and place it at:

```text
data/Reviews.csv
```

Then run:

```bash
make batch-amazon
```

Custom local path:

```bash
make batch-amazon AMAZON_REVIEWS_CSV=/path/to/Reviews.csv
```

HDFS path:

```bash
make batch-amazon AMAZON_REVIEWS_CSV=hdfs://localhost:9000/data/Reviews.csv
```

Path C, live streaming demo:

```bash
make api
make spark-storage
cd frontend && npm run dev
```

Submit a review from the Products page. Analytics are eventually consistent: a successful API
response means the review is queued in Kafka; Spark and Hive-backed analytics update after the
stream writes silver data.

The batch job reads CSV with headers, inferred schema, multiline support, and quote escaping. It
requires `Id`, `ProductId`, `UserId`, `Score`, `Text`, and `Time`, writes cleaned raw rows to
`/reviewstream/bronze/amazon_reviews_raw`, and appends normalized Parquet rows to
`/reviewstream/silver/reviews_enriched`.

## Live Streaming

Start the API:

```bash
make api
```

Start the Spark storage stream:

```bash
make spark-storage
```

Submit a review from the Products page or with:

```bash
make test-review
```

Analytics are eventually consistent: a successful API response means the review is queued in
Kafka; Spark and Hive-backed analytics update after the stream writes silver data.

## Product Catalog And Review API

Catalog endpoints do not depend on Hive, Kafka, Spark, or HDFS:

```text
GET /products
GET /products/{product_id}
```

Client review endpoint:

```text
POST /products/{product_id}/reviews
```

Request body:

```json
{"score": 5, "text": "Great product, fresh and tasty."}
```

## Hive

Initialize and query Hive:

```bash
make hive-metastore-init
make hive-wait
make hive-init
make hive-tables
make hive-query
```

Hive table:

```text
database: reviewstream
table: reviews_enriched
location: /reviewstream/silver/reviews_enriched
```

## API Endpoints

Core:

- `GET /`
- `GET /health`
- `GET /products`
- `GET /products/{product_id}`
- `POST /products/{product_id}/reviews`
- `POST /reviews`

Analytics:

- `GET /analytics`
- `GET /analytics/summary`
- `GET /analytics/sentiment`
- `GET /analytics/products?limit=10`
- `GET /analytics/score-distribution`
- `GET /analytics/top-products?limit=10&min_reviews=5`
- `GET /analytics/worst-products?limit=10&min_reviews=5`
- `GET /analytics/recent?limit=20`
- `GET /analytics/opinions?limit=50&sentiment=positive`
- `GET /analytics/negative-products?limit=10&min_reviews=3`
- `GET /analytics/sources`
- `GET /analytics/keywords/negative`
- `GET /analytics/keywords/positive`
- `GET /analytics/dashboard`

If Hive is unavailable, most analytics endpoints return:

```json
{"detail": "Analytics service is unavailable"}
```

`GET /analytics/dashboard` returns cached data with `status = cached` when a previous successful
snapshot exists.

## Services And Ports

| Service | Port |
| --- | --- |
| FastAPI | `8000` |
| Vite dashboard | `5173` |
| Kafka | `9092` |
| HDFS NameNode UI | `9870` |
| HDFS NameNode RPC | `9000` |
| HDFS DataNode | `9864`, `9866` |
| Hive Metastore | `9083` |
| Hive metadata DB | internal only |
| HiveServer2 | `10000`, `10002` |

## Tests And CI

Local checks:

```bash
make format
make check
pytest
mypy backend spark
docker compose config
cd frontend && npm run build
```

CI stays lightweight and does not start Kafka, HDFS, Spark, or Hive. It installs dependencies,
compiles Python, runs Ruff, Black check, mypy, pytest, and `docker compose config`.

## Troubleshooting

- API unreachable: run `make api`.
- Dashboard cannot reach API: use `cd frontend && npm run dev`; Vite proxies `/api` to
  `http://127.0.0.1:8000`.
- Hive unavailable: run `make hive-wait` and `make hive-init`.
- Empty dashboard: run `make batch-amazon` for historical data or start `make spark-storage` and
  submit live reviews.
- Missing CSV: put Amazon `Reviews.csv` at `data/Reviews.csv` or pass `AMAZON_REVIEWS_CSV=...`.

More detail:

- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Demo guide](docs/demo.md)
- [Troubleshooting](docs/troubleshooting.md)
