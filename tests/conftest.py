"""Shared fixtures: a running fake S&P Connect server and a client pointed at it."""

from __future__ import annotations

from collections.abc import AsyncIterator

import aiohttp
import pytest
import pytest_asyncio
from aiohttp.test_utils import TestServer

from custom_components.simpson_partners.api import AbstractAuth, SPConnectClient

from .mock_connect import VALID_TOKEN, MockConnectState, create_app, default_state


class FixedTokenAuth(AbstractAuth):
    """Auth that always returns the same token."""

    def __init__(self, token: str = VALID_TOKEN) -> None:
        """Store the token to hand out."""
        self.token = token

    async def async_get_access_token(self) -> str:
        """Return the fixed token."""
        return self.token


@pytest.fixture
def state() -> MockConnectState:
    """Return fresh mock-server state for each test."""
    return default_state()


@pytest_asyncio.fixture
async def server(state: MockConnectState) -> AsyncIterator[TestServer]:
    """Run the fake S&P Connect server for one test."""
    test_server = TestServer(create_app(state))
    await test_server.start_server()
    yield test_server
    await test_server.close()


@pytest_asyncio.fixture
async def session() -> AsyncIterator[aiohttp.ClientSession]:
    """Return an aiohttp session, closed after the test."""
    async with aiohttp.ClientSession() as client_session:
        yield client_session


@pytest.fixture
def auth() -> FixedTokenAuth:
    """Return auth holding the token the fake server accepts."""
    return FixedTokenAuth()


@pytest.fixture
def client(
    server: TestServer, session: aiohttp.ClientSession, auth: FixedTokenAuth
) -> SPConnectClient:
    """Return a client pointed at the fake server."""
    return SPConnectClient(session, auth, str(server.make_url("/")))
