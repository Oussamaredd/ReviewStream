# Local Development

Use this page for command-level local setup. For the evaluator flow, see
[demo.md](demo.md).

## Setup

```bash
make setup
make dev-install
cp .env.example .env
cd frontend && npm install && cd ..
```

## Infrastructure

```bash
make docker-up
make kafka-topic
make hdfs-wait
make hdfs-init
make hive-metastore-init
make hive-wait
make hive-init
```

## Historical Data

Quick sample data:

```bash
make seed-sample
```

The committed `data/sample_reviews.csv` is tiny and fake. Product IDs match the static catalog so
the Analytics page can show product names.

Full historical data:

Put Amazon Fine Food Reviews at:

```text
data/Reviews.csv
```

Download it from:

```text
https://www.kaggle.com/datasets/snap/amazon-fine-food-reviews
```

Extract `Reviews.csv` from the archive. Keep it local only; git ignores `data/Reviews.csv`.

Run:

```bash
make batch-amazon
```

Or:

```bash
make batch-amazon AMAZON_REVIEWS_CSV=/path/to/Reviews.csv
```

## Live Data

Start long-running processes in separate terminals:

```bash
make api
make spark-storage
make frontend-dev
```

Submit a review from `http://localhost:5173/products` or send a full event:

```bash
make test-review
```

The Products page submits only `score` and opinion text to
`POST /products/{product_id}/reviews`; the backend fills in product id, demo user id, and source
before publishing to Kafka.

## Checks

```bash
make dashboard-ready-check
make hive-tables
curl http://localhost:8000/analytics/dashboard
```

Dashboard states:

- Fresh: Hive query succeeded.
- Cached: Hive is unavailable, but the API serves the last successful dashboard snapshot.
- Sample: default dashboard requests show committed sample analytics if Hive is not ready and no
  cache exists.
- Strict cold start: direct strict API calls can still return `503` when Hive is unavailable and no
  cached dashboard exists.
- Empty: Hive reachable but the table has zero rows.

## Stop

```bash
make docker-down
```
