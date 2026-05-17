# Demo Guide

This is the shortest path to demonstrate both historical and live review analytics.

## 1. Prepare

```bash
make setup
make dev-install
cp .env.example .env
cd frontend && npm install && cd ..
```

For the quick demo, use the committed fake sample data:

```text
data/sample_reviews.csv
```

For the full historical demo, place the Amazon Fine Food Reviews CSV here:

```text
data/Reviews.csv
```

Download source:

```text
https://www.kaggle.com/datasets/snap/amazon-fine-food-reviews
```

Extract the Kaggle archive and copy `Reviews.csv` to `data/Reviews.csv`. Do not commit the CSV;
`data/Reviews.csv` is ignored and `data/.gitkeep` is the only tracked file in `data/`.

## 2. Run Infrastructure Setup

```bash
make docker-up
make kafka-wait
make kafka-topic
make hdfs-wait
make hdfs-init
make hive-metastore-init
make hive-wait
make hive-init
```

Print the full command order any time with:

```bash
make demo-full
```

## 3. Seed Data

Path A, quick demo:

```bash
make seed-sample
```

Path B, full historical demo:

```bash
make batch-amazon
```

Path C, live streaming demo after the services are running:

```bash
make spark-storage
```

Submit a review from the Products page.

Spark is not always running. Start `make spark-storage` only for the live-review part of the demo;
the seeded dashboard works without the streaming job.

## 4. Start Long-Running Services

Terminal 1:

```bash
make api
```

Terminal 2:

```bash
make spark-storage
```

Terminal 3:

```bash
make frontend-dev
```

Open:

```text
http://localhost:5173/products
http://localhost:5173/analytics
```

## 5. Demo Script

1. Open Products and choose a catalog item.
2. Submit only a score and opinion text.
3. Show the success message: "Review queued. Analytics will update after Spark and Hive catch up."
4. Open Analytics and confirm metrics, product tables, source counts, and opinion text are visible.
5. Wait for Spark to write silver data if demonstrating live reviews.
6. Watch dashboard totals update through polling.
7. Stop Hive temporarily after one successful dashboard response to show cached analytics.
8. Use `make consume` if you want to show Kafka messages from the terminal.
9. Open HDFS NameNode UI at `http://localhost:9870` if you want to show bronze/silver paths.

## 6. Dashboard States

- Fresh: Hive query succeeded.
- Cached: Hive is unavailable, but the API serves the last successful dashboard snapshot.
- Sample: first paint can show committed sample analytics. Automatic background Hive refresh is
  disabled by default for the lightweight demo; set `DASHBOARD_BACKGROUND_REFRESH_ENABLED=true`
  only when you want the API to warm the Hive cache on its own.
- Strict cold start: direct strict API calls can still return `503` when Hive is unavailable and no
  cache exists.
- Empty: Hive is available but no rows exist. The dashboard renders zero and empty-list defaults.

Live analytics are eventually consistent; Kafka acceptance happens before Spark and Hive reads
catch up.

## 7. Readiness Check

```bash
make dashboard-ready-check
```

The command checks HDFS readiness, expected HDFS paths, Hive readiness, Hive table availability,
and the API when it is running. It prints next steps instead of failing unclearly on optional
checks.
