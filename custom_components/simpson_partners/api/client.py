"""HTTP client for the S&P Connect /v1 API.

This is the only module that talks to S&P Connect. It sends authenticated
requests, turns every failure into an ``SPConnectError`` subclass, and returns
typed models. It holds no Home Assistant state, so it can later move into a
standalone PyPI library unchanged.

Start and stop resume and pause the charge (the firmware's ``control``
command, sent by S&P Connect). S&P Connect refuses them with 409 for chargers
it cannot pause reliably; see Architecture.md.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from http import HTTPStatus

import aiohttp

from ..const import (
    API_VERSION_PATH,
    MAX_SCHEDULE_WINDOWS,
    PATH_CHARGER,
    PATH_CHARGERS,
    PATH_COMMAND,
    PATH_CURRENT_LIMIT,
    PATH_SCHEDULE,
    PATH_SESSIONS,
    PATH_START,
    PATH_STATUS,
    PATH_STOP,
    PATH_TELEMETRY,
    REQUEST_TIMEOUT_SECONDS,
)
from .auth import AbstractAuth
from .exceptions import (
    SPConnectAuthError,
    SPConnectChargerOfflineError,
    SPConnectConnectionError,
    SPConnectNotFoundError,
    SPConnectRateLimitError,
    SPConnectResponseError,
)
from .models import (
    Charger,
    ChargerStatus,
    ChargeSession,
    Command,
    ScheduleWindow,
    TelemetryReading,
)
from .parsing import JsonObject, as_object

_LOGGER = logging.getLogger(__name__)

ERROR_CHARGER_OFFLINE = "charger_offline"

type _Builder[T] = Callable[[JsonObject], T]


class SPConnectClient:
    """Typed access to one S&P Connect connection."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: AbstractAuth,
        base_url: str,
    ) -> None:
        """Create a client.

        The aiohttp session is injected (Home Assistant shares one per
        instance) and the base URL is a parameter so tests can point the client
        at a mock server.
        """
        self._session = session
        self._auth = auth
        self._root = base_url.rstrip("/") + API_VERSION_PATH
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)

    async def async_get_chargers(self) -> list[Charger]:
        """Return every charger this connection can see."""
        body = await self._request("GET", PATH_CHARGERS)
        return self._parse_list(body, "chargers", Charger.from_json)

    async def async_get_charger(self, charger_id: str) -> Charger:
        """Return one charger's details."""
        body = await self._request("GET", PATH_CHARGER.format(charger_id=charger_id))
        return self._parse(body, Charger.from_json)

    async def async_get_status(self, charger_id: str) -> ChargerStatus:
        """Return a charger's live status, including active faults."""
        body = await self._request("GET", PATH_STATUS.format(charger_id=charger_id))
        return self._parse(body, ChargerStatus.from_json)

    async def async_get_telemetry(self, charger_id: str) -> list[TelemetryReading]:
        """Return the charger's recent 1-minute readings."""
        body = await self._request("GET", PATH_TELEMETRY.format(charger_id=charger_id))
        return self._parse_list(body, "readings", TelemetryReading.from_json)

    async def async_get_sessions(self, charger_id: str) -> list[ChargeSession]:
        """Return the charger's recent completed charges."""
        body = await self._request("GET", PATH_SESSIONS.format(charger_id=charger_id))
        return self._parse_list(body, "sessions", ChargeSession.from_json)

    async def async_set_schedule(
        self, charger_id: str, windows: Sequence[ScheduleWindow]
    ) -> Command:
        """Replace the charging schedule; an empty list clears it."""
        if len(windows) > MAX_SCHEDULE_WINDOWS:
            raise ValueError(
                f"At most {MAX_SCHEDULE_WINDOWS} schedule windows are allowed"
            )
        payload: JsonObject = {"windows": [window.to_json() for window in windows]}
        body = await self._request(
            "PUT", PATH_SCHEDULE.format(charger_id=charger_id), payload
        )
        return self._parse(body, Command.from_json)

    async def async_set_current_limit(self, charger_id: str, amps: int) -> Command:
        """Set the owner's charging current limit, in amps."""
        body = await self._request(
            "PUT",
            PATH_CURRENT_LIMIT.format(charger_id=charger_id),
            {"amps": amps},
        )
        return self._parse(body, Command.from_json)

    async def async_start_charging(self, charger_id: str) -> Command:
        """Resume charging, or start it now if a schedule is holding it."""
        body = await self._request("POST", PATH_START.format(charger_id=charger_id))
        return self._parse(body, Command.from_json)

    async def async_stop_charging(self, charger_id: str) -> Command:
        """Pause charging; the car stays plugged in."""
        body = await self._request("POST", PATH_STOP.format(charger_id=charger_id))
        return self._parse(body, Command.from_json)

    async def async_get_command(self, command_id: str) -> Command:
        """Return the delivery state of a command sent earlier."""
        body = await self._request("GET", PATH_COMMAND.format(command_id=command_id))
        return self._parse(body, Command.from_json)

    async def _request(
        self, method: str, path: str, payload: JsonObject | None = None
    ) -> object:
        """Send one request and return its decoded JSON body."""
        token = await self._auth.async_get_access_token()
        url = self._root + path
        _LOGGER.debug("S&P Connect request %s %s", method, path)
        try:
            async with self._session.request(
                method,
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=self._timeout,
            ) as response:
                if response.status >= HTTPStatus.BAD_REQUEST:
                    await self._raise_for_status(response, method, path)
                try:
                    body: object = await response.json(content_type=None)
                except ValueError as err:
                    raise SPConnectResponseError(
                        f"{method} {path} returned a body that is not JSON",
                        response.status,
                    ) from err
        except TimeoutError as err:
            raise SPConnectConnectionError(
                f"{method} {path} timed out after {REQUEST_TIMEOUT_SECONDS}s"
            ) from err
        except aiohttp.ClientError as err:
            raise SPConnectConnectionError(f"{method} {path} failed: {err}") from err
        _LOGGER.debug("S&P Connect response %s %s: %s", method, path, response.status)
        return body

    @staticmethod
    async def _raise_for_status(
        response: aiohttp.ClientResponse, method: str, path: str
    ) -> None:
        """Raise the exception that matches an error response."""
        status = response.status
        code, message = await _read_error(response)
        detail = f"{method} {path} returned {status}: {message or code or 'no detail'}"
        _LOGGER.debug("S&P Connect error %s", detail)
        if status == HTTPStatus.UNAUTHORIZED:
            raise SPConnectAuthError(detail)
        if status == HTTPStatus.NOT_FOUND:
            raise SPConnectNotFoundError(detail)
        if status == HTTPStatus.CONFLICT and code == ERROR_CHARGER_OFFLINE:
            raise SPConnectChargerOfflineError(detail)
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            raise SPConnectRateLimitError(detail, _retry_after(response))
        raise SPConnectResponseError(detail, status, code)

    @staticmethod
    def _parse[T](body: object, build: _Builder[T]) -> T:
        """Build one model, reporting a malformed body as a response error."""
        try:
            return build(as_object(body))
        except ValueError as err:
            raise SPConnectResponseError(
                f"Unexpected response from S&P Connect: {err}", HTTPStatus.OK
            ) from err

    @staticmethod
    def _parse_list[T](body: object, key: str, build: _Builder[T]) -> list[T]:
        """Build a list of models held under ``key`` in the response."""
        return SPConnectClient._parse(body, lambda data: _build_list(data, key, build))


def _build_list[T](data: JsonObject, key: str, build: _Builder[T]) -> list[T]:
    """Build each item of the list under ``key``; raise ValueError if absent."""
    items = data.get(key)
    if not isinstance(items, list):
        raise ValueError(f"{key} is missing or not a list")
    return [build(as_object(item)) for item in items]


async def _read_error(
    response: aiohttp.ClientResponse,
) -> tuple[str | None, str | None]:
    """Return the API's ``error`` code and ``message`` from an error body."""
    try:
        body = as_object(await response.json(content_type=None))
    except ValueError:
        # An error page that is not JSON (a proxy's HTML page, say) still has a
        # status; the caller reports that status without the API's detail.
        return None, None
    code = body.get("error")
    message = body.get("message")
    return (
        code if isinstance(code, str) else None,
        message if isinstance(message, str) else None,
    )


def _retry_after(response: aiohttp.ClientResponse) -> int | None:
    """Return the Retry-After header in seconds, if present and numeric."""
    value = response.headers.get("Retry-After")
    if value is None or not value.isdigit():
        return None
    return int(value)
