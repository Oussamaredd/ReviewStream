# API

Default base URL:

```text
http://localhost:8000
```

The API is unauthenticated and intended for local development only.

## Health

### GET /

Returns API status.

### GET /health

Returns health status and the configured Kafka topic.

Example:

```json
{
  "status": "ok",
  "kafka_topic": "reviews"
}
```

## Reviews

### POST /reviews

Publishes a review event to Kafka.

Request:

```json
{
  "product_id": "P001",
  "user_id": "client1",
  "score": 5,
  "text": "Great product",
  "source": "web"
}
```

Rules:

| Field | Rules |
| --- | --- |
| `product_id` | required, 1-100 characters |
| `user_id` | required, 1-100 characters |
| `score` | required integer, 1-5 |
| `text` | required, 1-2000 characters |
| `source` | optional, defaults to `web`, max 50 characters |

Response status: `201 Created`.

## Analytics

All analytics endpoints query Hive table `reviewstream.reviews_enriched`. If Hive is unavailable,
they return status `503`:

```json
{"detail": "Analytics service is unavailable"}
```

### GET /analytics

Compatibility aggregate containing:

- `summary`
- `sentiment`
- `products`

### GET /analytics/summary

Returns total reviews, average score, first review timestamp, and latest review timestamp.

### GET /analytics/sentiment

Returns counts grouped by score-based sentiment.

### GET /analytics/products?limit=10

Returns product aggregates ordered by review count and average score.

Parameters:

| Name | Default | Rules |
| --- | --- | --- |
| `limit` | `10` | integer, 1-100 |

### GET /analytics/score-distribution

Returns review counts grouped by numeric score.

### GET /analytics/top-products?limit=10&min_reviews=5

Returns products with the highest average score, filtered by minimum review count.

Parameters:

| Name | Default | Rules |
| --- | --- | --- |
| `limit` | `10` | integer, 1-100 |
| `min_reviews` | `5` | integer, 1-1,000,000 |

### GET /analytics/worst-products?limit=10&min_reviews=5

Returns products with the lowest average score, filtered by minimum review count.

### GET /analytics/recent?limit=20

Returns newest reviews ordered by `created_at DESC`.

Parameters:

| Name | Default | Rules |
| --- | --- | --- |
| `limit` | `20` | integer, 1-100 |

### GET /analytics/negative-products?limit=10&min_reviews=3

Returns products with the most negative reviews.

### GET /analytics/sources

Returns review counts grouped by source, such as `amazon_csv` and `web`.

### GET /analytics/keywords/negative

Returns the count of reviews containing one or more negative keywords.

### GET /analytics/keywords/positive

Returns the count of reviews containing one or more positive keywords.

### GET /analytics/dashboard

Returns the dashboard payload:

```json
{
  "summary": {},
  "sentiment": [],
  "score_distribution": [],
  "top_products": [],
  "worst_products": [],
  "negative_products": [],
  "recent_reviews": [],
  "sources": []
}
```
