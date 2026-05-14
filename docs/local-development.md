# Local Development

These commands assume Python 3.12, Docker, and Docker Compose are available.

ReviewStream is a local/demo project. The API and services are unauthenticated and should not be
published to the public internet.

## Setup

```bash
make setup
make dev-install
cp .env.example .env
```

## Start Infrastructure

```bash
make docker-up
make kafka-topic
make hdfs-wait
make hdfs-init
make hive-metastore-init
make hive-wait
make hive-init
```

Use these commands to inspect the stack:

```bash
make docker-logs
make hdfs-ls
make hive-tables
make hive-query
```

## Run The API

Open a separate terminal:

```bash
make api
```

Check health:

```bash
curl http://localhost:8000/health
```

## Run The Storage Stream

Open a separate terminal:

```bash
make spark-storage
```

The Spark job should keep running while you submit reviews. It writes bronze JSON and silver
Parquet data to HDFS.

## Submit Data

```bash
make test-review
```

Or:

```bash
curl -X POST http://localhost:8000/reviews \
  -H "Content-Type: application/json" \
  -d '{"product_id":"P001","user_id":"client1","score":5,"text":"Great product","source":"web"}'
```

## Query Hive And Analytics

```bash
make hive-tables
make hive-query
curl http://localhost:8000/analytics/summary
curl http://localhost:8000/analytics/sentiment
curl http://localhost:8000/analytics/products
curl http://localhost:8000/analytics
```

## Run Checks

```bash
make format
make check
pytest
mypy backend spark
docker compose config
```

The pytest suite mocks Hive access, so it does not need Docker services to be running.

## Stop Services

```bash
make docker-down
```
