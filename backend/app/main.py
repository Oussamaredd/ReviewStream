from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .analytics import router as analytics_router
from .catalog import get_product, list_products
from .config import settings
from .models import ProductReviewIn, ReviewEvent, ReviewIn
from .producer import close_producer, send_review


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    close_producer()


app = FastAPI(
    title="ReviewStream API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "app": "ReviewStream API",
        "status": "running",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "kafka_topic": settings.kafka_topic,
    }


def queue_review(review: ReviewIn) -> dict[str, object]:
    event = ReviewEvent.from_review(review).model_dump()

    try:
        kafka_metadata = send_review(event)

        return {
            "message": "Review sent to Kafka",
            "kafka": kafka_metadata,
            "review": event,
        }

    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {error}") from error


@app.get("/products")
def get_products() -> list[dict[str, object]]:
    return list_products()


@app.get("/products/{product_id}")
def get_catalog_product(product_id: str) -> dict[str, object]:
    product = get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product.model_dump()


@app.post("/products/{product_id}/reviews", status_code=201)
def create_product_review(product_id: str, review: ProductReviewIn) -> dict[str, object]:
    if get_product(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return queue_review(
        ReviewIn(
            product_id=product_id,
            user_id="web-client",
            score=review.score,
            text=review.text,
            source="web",
        )
    )


@app.post("/reviews", status_code=201)
def create_review(review: ReviewIn) -> dict[str, object]:
    return queue_review(review)


app.include_router(analytics_router)
