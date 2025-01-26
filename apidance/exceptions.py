class AuthenticationError(Exception):
    """Raised when authentication fails."""


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""


class ValidationError(Exception):
    """Raised when request validation fails."""


class TweetNotFoundError(Exception):
    """Raised when tweet is not found."""


class UserNotFoundError(Exception):
    """Raised when user is not found."""


class InsufficientCreditsError(Exception):
    "Raised when the account has insufficient API credits"


class PremiumRequiredError(Exception):
    "Upgrade to premium to use this feature"


class TimeoutError(Exception):
    "Raised when a request times out"


class InvalidUserIdError(Exception):
    "Raised when user ID format is invalid"


class AccountSuspendedError(Exception):
    "Raised when the account is suspended"
