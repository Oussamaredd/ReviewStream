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
cd frontend && npm run dev
```

Submit a sample review:

```bash
make test-review
```

## Checks

```bash
make dashboard-ready-check
make hive-tables
curl http://localhost:8000/analytics/dashboard
```

## Stop

```bash
make docker-down
```
