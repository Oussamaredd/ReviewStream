# Troubleshooting

## API Is Not Reachable

Run:

```bash
make api
```

Check:

```bash
curl http://localhost:8000/health
```

## Review Submission Returns 503

The product review endpoint publishes to Kafka before Spark and Hive see the event. If Kafka is
still starting, stopped, or the API is using the wrong bootstrap address, the API returns a friendly
`503` instead of hanging on the form.

Run:

```bash
make docker-up
make kafka-wait
make kafka-topic
make kafka-health
```

For host-run FastAPI (`make api`), use:

```text
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
```

If you changed `docker-compose.yml`, recreate Kafka so advertised listeners and health checks are
applied:

```bash
docker compose up -d --remove-orphans --force-recreate kafka
make kafka-wait
make kafka-topic
```

The local stack uses one Kafka container in KRaft mode. There is no ZooKeeper or Kafka UI
container.

## Dashboard Cannot Reach API

Use the Vite dev server:

```bash
cd frontend && npm run dev
```

The Vite proxy maps `/api` to `http://127.0.0.1:8000`.

## Hive Analytics Return 503

Most analytics endpoints return `503` when Hive is down, HiveServer2 is still starting, the
metastore is not initialized, or the external table has not been created.

Run:

```bash
make hive-wait
make hive-init
make seed-sample
make dashboard-ready-check
```

The API intentionally hides PyHive/Thrift exception details and returns:

```json
{"detail": "Analytics service is unavailable"}
```

## Dashboard Shows Cached Data

`GET /analytics/dashboard` is the only analytics endpoint with a process-local fallback cache. If
Hive fails after a previous successful dashboard response, the API returns the last successful
snapshot with:

```json
{
  "status": "cached",
  "stale": true,
  "warning": "Hive is unavailable. Showing last successful analytics snapshot."
}
```

Fix Hive and refresh:

```bash
make hive-wait
make hive-init
make dashboard-ready-check
```

The cache is process-local. Restarting the API clears it.

## Dashboard Cold Start Message

If Hive is unavailable and the API has no cached dashboard snapshot yet, the frontend shows a sample
analytics snapshot from `data/sample_reviews.csv` after the fresh Hive attempt fails. Direct API
calls without sample fallback still return:

```text
Analytics are not ready yet. Start Hive, initialize the table, or seed sample data.
```

Run:

```bash
make docker-up
make hdfs-wait
make hdfs-init
make hive-metastore-init
make hive-wait
make hive-init
make seed-sample
```

The Analytics page also stores the last non-sample dashboard in browser localStorage, so reloads can
show previous analytics immediately.

If Hive aggregate queries are slow but eventually succeed, keep the default sample/cache dashboard
for the live demo and use strict dashboard calls only when you need to verify fresh Hive analytics.
Set `DASHBOARD_BACKGROUND_REFRESH_ENABLED=true` to let the API refresh the real dashboard cache in
the background. `HIVE_SOCKET_TIMEOUT_SECONDS` controls how long the API waits on a Hive socket
before treating the refresh as unavailable.

## Spark Stream Fails After Recreating Kafka

The local Kafka container is intentionally stateless, while Spark checkpoints live in HDFS. If Kafka
is recreated, old checkpoint offsets can be higher than the new topic offsets. The demo defaults
`SPARK_KAFKA_FAIL_ON_DATA_LOSS=false` so Spark moves past that local reset instead of crashing.
Set it to `true` only when you want strict production-style offset loss failures.

## Dashboard Has No Data

For quick sample data:

```bash
make seed-sample
```

For full historical data:

```bash
make batch-amazon
```

For live data:

```bash
make spark-storage
make test-review
```

Remember that live analytics are eventually consistent. Kafka acceptance happens before Spark and
Hive table reads catch up.

## Amazon CSV Is Missing

Place the file at:

```text
data/Reviews.csv
```

Download the dataset from Kaggle:

```text
https://www.kaggle.com/datasets/snap/amazon-fine-food-reviews
```

Extract `Reviews.csv` from the archive. The file is ignored by git and should stay local.

Or pass a path:

```bash
make batch-amazon AMAZON_REVIEWS_CSV=/path/to/Reviews.csv
```

## HDFS Paths Are Missing

Run:

```bash
make hdfs-wait
make hdfs-init
```

Then:

```bash
make hdfs-ls
```

## Hive Metastore Problems

Initialize the metastore schema:

```bash
make hive-metastore-init
```

Then recreate the external table:

```bash
make hive-init
```

`hive-metastore-db` is PostgreSQL used only to persist Hive Metastore metadata. It does not store
review files; HDFS stores the actual bronze and silver data.

## High CPU Or Memory Usage

Keep only the services needed for the current demo step running. Spark starts only when a Spark
Make target runs, so stop `make spark-storage` when you are not showing live reviews.

The default Spark Make targets use `local[1]`, one shuffle partition, and a 30-second streaming
trigger. If your machine is still under load, prefer `make seed-sample` over the full Amazon CSV
ingest and avoid running `make spark-analytics` or `make spark-stream` alongside
`make spark-storage`.

## CI Does Not Start Docker Services

This is expected. CI only validates code, tests, and Compose configuration. It does not run Kafka,
Spark, HDFS, or Hive.
