# API

The ReviewStream API is a local/demo FastAPI service. It is unauthenticated and not intended for
public internet exposure.

Default base URL:

```text
http://localhost:8000
```

## GET /

Returns basic API status.

```bash
curl http://localhost:8000/
```

Example response:

```json
{
  "app": "ReviewStream API",
  "status": "running"
}
```

## GET /health

Returns health status and the configured Kafka topic.

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "ok",
  "kafka_topic": "reviews"
}
```

## POST /reviews

Accepts a product review and publishes a review event to Kafka topic `reviews`.

```bash
curl -X POST http://localhost:8000/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "P001",
    "user_id": "client1",
    "score": 5,
    "text": "Great product",
    "source": "web"
  }'
```

Request fields:

| Field | Type | Rules |
| --- | --- | --- |
| `product_id` | string | required, 1-100 chars |
| `user_id` | string | required, 1-100 chars |
| `score` | integer | required, 1-5 |
| `text` | string | required, 1-2000 chars |
| `source` | string | optional, defaults to `web`, max 50 chars |

Successful response status: `201 Created`.

The response includes Kafka metadata and the emitted review event, including generated
`review_id` and `created_at` fields.

## GET /analytics/summary

Queries Hive and returns review totals.

```bash
curl http://localhost:8000/analytics/summary
```

Example response:

```json
{
  "total_reviews": 12,
  "average_score": 4.25,
  "first_review_at": "2026-05-14T10:00:00",
  "last_review_at": "2026-05-14T10:30:00"
}
```

## GET /analytics/sentiment

Queries Hive and returns review counts by sentiment.

```bash
curl http://localhost:8000/analytics/sentiment
```

Example response:

```json
[
  {
    "sentiment": "positive",
    "review_count": 8
  },
  {
    "sentiment": "neutral",
    "review_count": 3
  },
  {
    "sentiment": "negative",
    "review_count": 1
  }
]
```

## GET /analytics/products

Queries Hive and returns product review aggregates ordered by review count and average score.

Optional query parameter:

| Name | Type | Rules | Default |
| --- | --- | --- | --- |
| `limit` | integer | `1 <= limit <= 100` | `10` |

```bash
curl http://localhost:8000/analytics/products
curl http://localhost:8000/analytics/products?limit=5
```

Example response:

```json
[
  {
    "product_id": "P001",
    "review_count": 7,
    "average_score": 4.71
  }
]
```

## GET /analytics

Queries Hive and returns summary, sentiment, and top product analytics in one payload.

```bash
curl http://localhost:8000/analytics
```

Example response:

```json
{
  "summary": {
    "total_reviews": 12,
    "average_score": 4.25,
    "first_review_at": "2026-05-14T10:00:00",
    "last_review_at": "2026-05-14T10:30:00"
  },
  "sentiment": [
    {
      "sentiment": "positive",
      "review_count": 8
    }
  ],
  "products": [
    {
      "product_id": "P001",
      "review_count": 7,
      "average_score": 4.71
    }
  ]
}
```

## Analytics Error Response

If Hive is unavailable or a Hive query fails, analytics endpoints return:

```json
{
  "detail": "Analytics service is unavailable"
}
```

Status code: `503 Service Unavailable`.
