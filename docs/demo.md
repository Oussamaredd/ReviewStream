# Demo Guide

This is the shortest path to demonstrate both historical and live review analytics.

## 1. Prepare

```bash
make setup
make dev-install
cp .env.example .env
cd frontend && npm install && cd ..
```

Place the Amazon Fine Food Reviews CSV here:

```text
data/Reviews.csv
```

Download source:

```text
https://www.kaggle.com/datasets/snap/amazon-fine-food-reviews
```

Extract the Kaggle archive and copy `Reviews.csv` to `data/Reviews.csv`. Do not commit the CSV;
`data/Reviews.csv` is ignored and `data/.gitkeep` is the only tracked file in `data/`.

## 2. Run Finite Setup

```bash
make demo-full
```

This runs:

```text
docker-up
kafka-topic
hdfs-wait
hdfs-init
hive-metastore-init
hive-wait
hive-init
batch-amazon when data/Reviews.csv exists
```

It does not leave API or Spark streaming running forever; those are started separately.

## 3. Start Long-Running Services

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
cd frontend && npm run dev
```

Open:

```text
http://localhost:5173
```

## 4. Demo Script

1. Open the dashboard and confirm historical metrics are visible.
2. Submit a live review from the form.
3. Show the success message with Kafka offset.
4. Wait for Spark to write silver data.
5. Watch dashboard totals update through polling.
6. Open Kafka UI at `http://localhost:8080` if you want to show the live topic.
7. Open HDFS NameNode UI at `http://localhost:9870` if you want to show bronze/silver paths.

## 5. Readiness Check

```bash
make dashboard-ready-check
```

The command checks HDFS paths, Hive table availability, and the dashboard analytics API when the
API is running.
