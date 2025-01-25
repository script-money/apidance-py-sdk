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


class InvalidUserIdError(Exception):
    "Raised when user ID format is invalid"
    pass


class AccountSuspendedError(Exception):
    "Raised when the account is suspended"
    pass
