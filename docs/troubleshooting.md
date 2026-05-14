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

Run:

```bash
make hive-wait
make hive-init
make hive-tables
```

The API intentionally hides PyHive/Thrift exception details and returns:

```json
{"detail": "Analytics service is unavailable"}
```

## Dashboard Has No Data

For historical data:

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
