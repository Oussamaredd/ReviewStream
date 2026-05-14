# ReviewStream

ReviewStream is a local Big Data ecommerce review analytics project. It demonstrates two data
paths that land in the same Hive-backed analytics table:

- Historical batch ingestion from Amazon Fine Food Reviews `Reviews.csv`.
- Live review streaming from the dashboard/API through Kafka and Spark.

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
    -> Vue dashboard

Live path:
  Vue dashboard
    -> FastAPI POST /reviews
    -> Kafka topic reviews
    -> Spark Structured Streaming
    -> HDFS bronze reviews_raw
    -> HDFS silver reviews_enriched
    -> Hive reviewstream.reviews_enriched
    -> FastAPI analytics
    -> Vue dashboard
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

Do not commit `data/Reviews.csv`; `data/` is ignored except for `data/.gitkeep`.

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
HDFS_BASE_PATH=hdfs://namenode:9000/reviewstream
```

## Full Local Demo

Place `Reviews.csv` at `data/Reviews.csv`, then run the finite setup:

```bash
make demo-full
```

`demo-full` starts infrastructure, initializes HDFS/Hive, runs historical batch ingestion when the
CSV exists, and then prints the long-running commands to start separately.

Start these in separate terminals:

```bash
make api
make spark-storage
cd frontend && npm run dev
```

Open the dashboard at the Vite URL, usually:

```text
http://localhost:5173
```

Check readiness:

```bash
make dashboard-ready-check
```

## Historical Batch Ingestion

Download the Amazon Fine Food Reviews dataset from Kaggle:

```text
https://www.kaggle.com/datasets/snap/amazon-fine-food-reviews
```

Extract `Reviews.csv` and place it at:

```text
data/Reviews.csv
```

The CSV is intentionally ignored by git. Commit only `data/.gitkeep` so the expected local
directory exists for new clones.

Default:

```bash
make batch-amazon
```

Custom local path:

```bash
make batch-amazon AMAZON_REVIEWS_CSV=/path/to/Reviews.csv
```

HDFS path:

```bash
make batch-amazon AMAZON_REVIEWS_CSV=hdfs://namenode:9000/data/Reviews.csv
```

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

Submit a review from the dashboard or with:

```bash
make test-review
```

Analytics are eventually consistent: a successful API response means the review is queued in
Kafka; Spark and Hive-backed analytics update after the stream writes silver data.

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
- `GET /analytics/negative-products?limit=10&min_reviews=3`
- `GET /analytics/sources`
- `GET /analytics/keywords/negative`
- `GET /analytics/keywords/positive`
- `GET /analytics/dashboard`

If Hive is unavailable, analytics endpoints return:

```json
{"detail": "Analytics service is unavailable"}
```

## Services And Ports

| Service | Port |
| --- | --- |
| FastAPI | `8000` |
| Vite dashboard | `5173` |
| Kafka | `9092` |
| Kafka UI | `8080` |
| HDFS NameNode UI | `9870` |
| HDFS NameNode RPC | `9000` |
| HDFS DataNode | `9864`, `9866` |
| Hive Metastore | `9083` |
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
