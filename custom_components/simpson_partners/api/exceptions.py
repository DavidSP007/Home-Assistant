"""Exceptions raised by the S&P Connect API client.

Every failure the client can produce is one of these types, so callers (the
coordinator, the config flow) branch on the class and never on message text.
"""

from __future__ import annotations


class SPConnectError(Exception):
    """Base class for every S&P Connect client error."""


class SPConnectConnectionError(SPConnectError):
    """The API could not be reached (network failure or timeout)."""


class SPConnectAuthError(SPConnectError):
    """The access token was rejected; the connection may have been revoked."""


class SPConnectNotFoundError(SPConnectError):
    """The charger or command does not exist on this connection."""


class SPConnectChargerOfflineError(SPConnectError):
    """A command was refused because the charger is offline (409)."""


class SPConnectRateLimitError(SPConnectError):
    """Too many requests (429); retry after the given number of seconds."""

    def __init__(self, message: str, retry_after: int | None) -> None:
        """Store the server's Retry-After value alongside the message."""
        super().__init__(message)
        self.retry_after = retry_after


class SPConnectResponseError(SPConnectError):
    """The API answered with an unexpected status or an unreadable body."""

    def __init__(self, message: str, status: int, code: str | None = None) -> None:
        """Store the HTTP status and the API's machine error code, if any."""
        super().__init__(message)
        self.status = status
        self.code = code
