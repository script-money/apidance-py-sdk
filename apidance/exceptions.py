class AuthenticationError(Exception):
    "Raised when authentication fails"
    pass


class RateLimitError(Exception):
    "Raised when API rate limit is exceeded"
    pass


class InsufficientCreditsError(Exception):
    "Raised when the account has insufficient API credits"
    pass


class TimeoutError(Exception):
    "Raised when a request times out"
    pass
