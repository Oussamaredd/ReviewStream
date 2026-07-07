class ReviewPublishUnavailableError(RuntimeError):
    """Raised when a review cannot be published to the event stream."""


class ProductNotFoundError(LookupError):
    """Raised when a catalog-backed review references an unknown product."""
