import logging

from fastapi import APIRouter, HTTPException

from backend.reviewstream.reviews.application.dto import ReviewSubmissionResult
from backend.reviewstream.reviews.application.errors import (
    ProductNotFoundError,
    ReviewPublishUnavailableError,
)
from backend.reviewstream.reviews.application.use_cases import (
    SubmitProductReviewUseCase,
    SubmitReviewUseCase,
)
from backend.reviewstream.reviews.domain.errors import ReviewDomainError
from backend.reviewstream.reviews.interfaces.http.responses import ReviewSubmissionResponse
from backend.reviewstream.reviews.interfaces.http.schemas import ProductReviewIn, ReviewIn

logger = logging.getLogger(__name__)


def create_router(
    submit_review: SubmitReviewUseCase,
    submit_product_review: SubmitProductReviewUseCase,
) -> APIRouter:
    router = APIRouter(tags=["reviews"])

    def review_submission_response(result: ReviewSubmissionResult) -> dict[str, object]:
        return ReviewSubmissionResponse.from_result(result).to_payload()

    @router.post(
        "/products/{product_id}/reviews",
        status_code=201,
        response_model=ReviewSubmissionResponse,
    )
    def create_product_review(product_id: str, review: ProductReviewIn) -> dict[str, object]:
        try:
            return review_submission_response(
                submit_product_review.execute(review.to_command(product_id))
            )
        except ProductNotFoundError as error:
            raise HTTPException(status_code=404, detail="Product not found") from error
        except ReviewPublishUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ReviewDomainError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:  # pragma: no cover - defensive handler
            logger.exception("Unexpected product review submission failure")
            raise HTTPException(status_code=500, detail="Review submission failed") from error

    @router.post("/reviews", status_code=201, response_model=ReviewSubmissionResponse)
    def create_review(review: ReviewIn) -> dict[str, object]:
        try:
            return review_submission_response(submit_review.execute(review.to_command()))
        except ReviewPublishUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ReviewDomainError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:  # pragma: no cover - defensive handler
            logger.exception("Unexpected review submission failure")
            raise HTTPException(status_code=500, detail="Review submission failed") from error

    return router
