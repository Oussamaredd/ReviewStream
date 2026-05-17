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

### GET /health/kafka

Actively probes Kafka from the API process. Use this when review submission returns `503`.

Example:

```json
{
  "status": "ok",
  "available": true,
  "bootstrap_servers": ["127.0.0.1:9092"],
  "topic": "reviews"
}
```

## Reviews

### GET /products

Returns the static ecommerce demo catalog. This endpoint does not query Kafka, Spark, HDFS, or
Hive.

### GET /products/{product_id}

Returns one catalog product or `404`:

```json
{"detail": "Product not found"}
```

### POST /products/{product_id}/reviews

Client-facing review endpoint used by the Products page. The user submits only score and opinion
text. The backend validates the catalog product, sets `user_id = web-client`, sets `source = web`,
creates the review event, and publishes it to Kafka.

Request:

```json
{
  "score": 5,
  "text": "Great product, fresh and tasty."
}
```

Rules:

| Field | Rules |
| --- | --- |
| `score` | required integer, 1-5 |
| `text` | required, 1-2000 characters |

Response status: `201 Created`.

### POST /reviews

Publishes a full review event to Kafka. This endpoint remains available for API tests and direct
integration calls.

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

Analytics endpoints query Hive table `reviewstream.reviews_enriched`. Most analytics endpoints
return status `503` when Hive is unavailable:

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

Returns newest reviews ordered by `created_at DESC`, including review/opinion text fields:

- `product_id`
- `product_name` when the static catalog knows the product
- `user_id`
- `score`
- `sentiment`
- `text`
- `source`
- `review_id`
- `created_at`
- `text_length`
- `word_count`
- `has_negative_keywords`
- `has_positive_keywords`

Parameters:

| Name | Default | Rules |
| --- | --- | --- |
| `limit` | `20` | integer, 1-100 |

### GET /analytics/opinions?limit=50&sentiment=positive

Returns newest review/opinion text rows. `sentiment` is optional and must be one of `positive`,
`neutral`, or `negative` when provided.

Parameters:

| Name | Default | Rules |
| --- | --- | --- |
| `limit` | `50` | integer, 1-100 |
| `sentiment` | none | `positive`, `neutral`, or `negative` |

### GET /analytics/negative-products?limit=10&min_reviews=3

Returns products with the most negative reviews.

### GET /analytics/sources

Returns review counts grouped by source, such as `amazon_csv` and `web`.

### GET /analytics/keywords/negative

Returns the count of reviews containing one or more negative keywords.

### GET /analytics/keywords/positive

Returns the count of reviews containing one or more positive keywords.

### GET /analytics/dashboard

Returns the dashboard payload. Successful responses are cached in process memory.

```json
{
  "status": "fresh",
  "stale": false,
  "generated_at": "2026-01-01T00:00:00+00:00",
  "summary": {
    "total_reviews": 0,
    "average_score": 0,
    "first_review_at": null,
    "last_review_at": null
  },
  "sentiment": [],
  "score_distribution": [],
  "top_products": [],
  "worst_products": [],
  "negative_products": [],
  "recent_reviews": [],
  "sources": [],
  "opinions": [],
  "negative_keywords": {"keyword_type": "negative", "matching_reviews": 0},
  "positive_keywords": {"keyword_type": "positive", "matching_reviews": 0}
}
```

Dashboard states:

- Fresh: Hive query succeeded; response has `status = fresh` and `stale = false`.
- Cached: Hive failed after a previous success; response has `status = cached`, `stale = true`,
  and `warning = "Hive is unavailable. Showing last successful analytics snapshot."`.
- Sample: default dashboard requests use `prefer_cache=true&allow_sample=true`. If no process
  cache exists yet, the API returns analytics computed from committed `data/sample_reviews.csv`
  with `status = sample`. Automatic background Hive refresh is disabled by default for local demos;
  enable `DASHBOARD_BACKGROUND_REFRESH_ENABLED=true` to refresh the process cache asynchronously.
- Strict cold start: callers that request
  `/analytics/dashboard?prefer_cache=false&allow_sample=false` get `503` when Hive fails before
  any successful dashboard.
- Empty: Hive is reachable but has zero rows; response is `200` with zero and empty-list defaults.
