# Backend Clean Architecture

ReviewStream is organized as a modular monolith. The runtime is still one FastAPI process, but the
backend code is split into bounded contexts that can become separate services later.

The public ASGI entry point remains:

```text
backend.app.main:app
```

That module is only a compatibility shim for Makefile and uvicorn commands. The real application
factory and dependency wiring live in:

```text
backend/reviewstream/bootstrap.py
```

## Dependency Rule

The backend follows this direction:

```text
interfaces/http -> application -> domain
                         ^
                         |
                  infrastructure
```

The practical rules are:

- HTTP routers parse requests and translate errors into HTTP responses.
- Application services and use cases coordinate workflows.
- Domain models represent business meaning and domain events.
- Application ports describe external capabilities the use cases need.
- Infrastructure adapters talk to Kafka, Hive, files, caches, or other processes.
- `bootstrap.py` is the composition root that wires adapters into ports.
- `main.py` creates the app; it does not own endpoint behavior.

## Package Layout

```text
backend/
  app/
    main.py                         # legacy uvicorn import shim

  reviewstream/
    main.py                         # app = create_app()
    bootstrap.py                    # dependency container and router registration

    platform/
      config.py                     # environment-backed settings
      hive_client.py                # low-level Hive/PyHive client

    reviews/
      domain/
        models.py                   # Review entity/value data
        events.py                   # ReviewSubmitted domain event
        errors.py
      application/
        commands.py                 # input commands for use cases
        dto.py                      # use-case results returned to interfaces
        errors.py                   # application-level workflow failures
        ports.py                    # ReviewPublisher, ProductLookup
        use_cases.py                # SubmitReviewUseCase, SubmitProductReviewUseCase
      infrastructure/
        kafka_review_publisher.py   # Kafka adapter
      interfaces/http/
        schemas.py                  # FastAPI/Pydantic request schemas
        responses.py                # FastAPI/Pydantic response schemas
        router.py                   # POST /reviews and product review endpoints

    catalog/
      domain/
        models.py                   # Product domain model
      application/
        ports.py                    # ProductRepository
        queries.py                  # CatalogQueryService
      infrastructure/
        in_memory_catalog_repository.py
      interfaces/http/
        schemas.py
        router.py                   # GET /products endpoints

    analytics/
      application/
        queries.py                  # AnalyticsQueryService
        dashboard_service.py        # dashboard cache/fallback workflow
        dashboard_payloads.py       # dashboard normalization and safety checks
        ports.py                    # AnalyticsRepository, DashboardCache, sample provider
        types.py
      infrastructure/
        hive_analytics_repository.py
        hive_sql.py
        dashboard_cache.py
        sample_dashboard.py
      interfaces/http/
        router.py                   # GET /analytics endpoints

    health/
      application/
        checks.py
        ports.py
      infrastructure/
        kafka_health_probe.py
      interfaces/http/
        responses.py
        router.py                   # /, /health, /health/kafka
```

## Bounded Contexts

Reviews owns live review submission. It validates the command into a domain `Review`, creates a
`ReviewSubmitted` event, and publishes through the `ReviewPublisher` port. Kafka is only one adapter
for that port. Review use cases return a `ReviewSubmissionResult`; the HTTP layer maps that
application DTO to the current API response shape, including the legacy `kafka` field.

Catalog owns product lookup. The current adapter is an in-memory demo catalog, but the application
service depends on a `ProductRepository` port so the catalog could move to a database or service API.

Analytics owns read-side reporting. It is intentionally less domain-heavy because it is a query/read
model over Hive data. SQL and PyHive calls stay in `analytics/infrastructure`; the router only sees an
`AnalyticsQueryService`. Query limits, minimum-review thresholds, and sentiment filters are validated
in the application service as well as at the FastAPI boundary, so the application contract is still
safe if another interface is added later.

Health owns operational probes. It depends on a Kafka probe port so health checks do not need to know
how reviews publish events. The current Kafka health adapter receives an injected probe callable from
the review publisher instead of importing review infrastructure directly.

Platform owns cross-cutting process concerns such as settings and low-level Hive connection helpers.
It should not contain feature workflows. Environment parsing goes through `Settings.from_env()`, which
keeps `.env` loading explicit and validates local defaults before the app is wired.

## Request Flows

Review submission:

```text
POST /products/{product_id}/reviews
  -> reviews/interfaces/http/router.py
  -> SubmitProductReviewUseCase
  -> ProductLookup port
  -> Review domain model
  -> ReviewSubmitted domain event
  -> ReviewPublisher port
  -> KafkaReviewPublisher
  -> Kafka topic reviews
```

The `KafkaReviewPublisher` is instance-owned and injected by `bootstrap.py`. It owns its producer and
shutdown lifecycle, which keeps tests and future service splits from depending on process-global
Kafka state. Module-level producer helpers remain only for backwards-compatible imports.

Analytics dashboard:

```text
GET /analytics/dashboard
  -> analytics/interfaces/http/router.py
  -> DashboardService
  -> AnalyticsQueryService
  -> AnalyticsRepository port
  -> HiveAnalyticsRepository
  -> Hive/PyHive
```

If Hive is unavailable, `DashboardService` owns the cache/sample fallback behavior. The router only
translates final application errors into HTTP responses.

The dashboard cache returns deep copies and protects reads/writes with a lock. Fresh dashboard
responses are the only payloads stored in the process cache; cached and sample responses are generated
as response views so callers cannot mutate shared cache state.

## Response Contracts

HTTP response models live in `interfaces/http` because they are transport contracts, not domain
objects. The review, catalog, and health endpoints expose explicit Pydantic response models. Analytics
endpoints currently return Hive-shaped dictionaries and lists because this demo API mirrors aggregate
read models from Hive; keep that flexibility at the HTTP edge and keep SQL/result validation in the
analytics application and infrastructure layers.

## Microservice Readiness

The code is not split into microservices yet. It is structured so the future split is mechanical:

```text
reviews service      -> reviews context + Kafka publisher
catalog service      -> catalog context + product storage
analytics API        -> analytics context + Hive/warehouse adapter
health/ops endpoints -> service-local health context
```

When a context becomes a service, replace local ports with network adapters. For example, `ProductLookup`
could be implemented by an HTTP/gRPC catalog client instead of the in-memory repository. The reviews
use cases would not need to know the difference.

The same applies to operational dependencies. Kafka publishing, Kafka health probing, Hive analytics,
sample-dashboard loading, and dashboard caching are all behind application ports or injected adapters,
so each can move behind a service API without changing domain models or HTTP request parsing.

## Adding Code

Use these placement rules:

- Add new HTTP endpoints under `*/interfaces/http/router.py`.
- Add request/response Pydantic schemas under `*/interfaces/http/schemas.py`.
- Add workflow logic under `*/application`.
- Add business invariants and domain events under `*/domain`.
- Add Kafka, Hive, filesystem, cache, database, or network code under `*/infrastructure`.
- Wire new adapters in `backend/reviewstream/bootstrap.py`.
- Keep `backend/app/main.py` as a shim only.
- Build route tests with `create_app(container)` and fake adapters when possible. `app.state.container`
  is available for debugging and compatibility, but new tests should prefer an explicit container.

Avoid these patterns:

- Do not add feature endpoints directly to `main.py`.
- Do not put SQL in routers.
- Do not call Kafka, Hive, Spark, HDFS, or files directly from domain models.
- Do not make application use cases depend on FastAPI classes.
- Do not bypass ports when a workflow depends on another context or external system.
- Do not add new process-global Kafka, Hive, cache, or settings state when it can be injected through
  the application container.
