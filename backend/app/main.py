from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import ReviewEvent, ReviewIn
from .producer import close_producer, send_review
from backend.app.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
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
def root():
    return {
        "app": "ReviewStream API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "kafka_topic": settings.kafka_topic,
    }


@app.post("/reviews", status_code=201)
def create_review(review: ReviewIn):
    event = ReviewEvent.from_review(review).model_dump()

    try:
        kafka_metadata = send_review(event)

        return {
            "message": "Review sent to Kafka",
            "kafka": kafka_metadata,
            "review": event,
        }

    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error))

    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {error}")


app.include_router(analytics_router)
