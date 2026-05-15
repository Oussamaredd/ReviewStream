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

If Hive is unavailable and the API has no cached dashboard snapshot yet, the frontend first shows a
sample analytics snapshot from `data/sample_reviews.csv`. Direct API calls without sample fallback
still return:

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
show previous analytics immediately while the API refreshes.

If Hive aggregate queries are slow but eventually succeed, leave the frontend on the Analytics page.
The API refreshes the real dashboard cache in the background. `HIVE_SOCKET_TIMEOUT_SECONDS` controls
how long the API waits on a Hive socket before treating the refresh as unavailable.

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

## CI Does Not Start Docker Services

This is expected. CI only validates code, tests, and Compose configuration. It does not run Kafka,
Spark, HDFS, or Hive.
