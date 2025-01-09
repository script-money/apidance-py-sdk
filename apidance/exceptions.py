class TwitterAPIError(Exception):
    """Base exception for Twitter API errors."""

    def __init__(self, message, code=None, **kwargs):
        super().__init__(message)
        self.code = code
        for key, value in kwargs.items():
            setattr(self, key, value)


class AuthenticationError(TwitterAPIError):
    """Raised when authentication fails (401 errors).

    Examples:
    - Invalid API key
    - Expired token
    - Invalid credentials
    """

    pass
