"""Exception classes for the Apidance SDK.

This module contains all the exceptions that can be raised by the Apidance SDK.
Exceptions are categorized into four groups:
1. Base exceptions (base class for all SDK exceptions)
2. Configuration exceptions (related to SDK configuration)
3. Apidance platform exceptions (related to the Apidance API platform)
4. Twitter platform exceptions (related to Twitter API errors)
"""


# -----------------------------------------------------------------------------
# Base Exceptions
# -----------------------------------------------------------------------------
class ApiDanceError(Exception):
    """Base class for all ApiDance exceptions."""

    pass


class TimeoutError(ApiDanceError):
    """Raised when a request times out."""

    pass


# -----------------------------------------------------------------------------
# Configuration Exceptions
# -----------------------------------------------------------------------------
class ConfigurationError(ApiDanceError):
    """Base class for all configuration-related exceptions."""

    pass


class ApiKeyError(ConfigurationError):
    """Raised when the APIDANCE_API_KEY is missing or invalid."""

    pass


class AuthTokenError(ConfigurationError):
    """Raised when the X_AUTH_TOKEN is missing or invalid."""

    pass


# -----------------------------------------------------------------------------
# Apidance Platform Exceptions
# -----------------------------------------------------------------------------
class ApidancePlatformError(ApiDanceError):
    """Base class for all Apidance platform-related exceptions."""

    pass


class RateLimitError(ApidancePlatformError):
    """Raised when Apidance platform rate limit is exceeded."""

    pass


class InsufficientCreditsError(ApidancePlatformError):
    """Raised when the account has insufficient API credits."""

    pass


# -----------------------------------------------------------------------------
# Twitter Platform Exceptions
# -----------------------------------------------------------------------------
class TwitterPlatformError(ApiDanceError):
    """Base class for all Twitter platform-related exceptions."""

    pass


class PremiumRequiredError(TwitterPlatformError):
    """Raised when a premium feature is requested with a non-premium account."""

    pass


class InvalidInputError(TwitterPlatformError):
    """Raised when the provided query is invalid or not found."""

    pass


class AuthenticationError(TwitterPlatformError):
    """Raised when authentication fails."""

    pass
