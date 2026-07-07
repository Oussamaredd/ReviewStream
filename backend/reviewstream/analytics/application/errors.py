class AnalyticsUnavailableError(RuntimeError):
    """Raised when analytics data cannot be queried from its backing store."""


class AnalyticsInputError(ValueError):
    """Raised when analytics query parameters are invalid outside the HTTP layer."""
