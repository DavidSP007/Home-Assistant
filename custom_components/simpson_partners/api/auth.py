"""Access-token provider used by the S&P Connect client.

The client depends on this abstraction rather than on Home Assistant's OAuth
machinery (dependency inversion): the config flow PR supplies an implementation
backed by Home Assistant's OAuth2 session, and tests supply a fixed token.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractAuth(ABC):
    """Supplies a valid S&P Connect access token for each request."""

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return an access token, refreshing it first if it has expired."""
