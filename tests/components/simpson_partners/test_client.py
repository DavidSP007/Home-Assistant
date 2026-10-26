"""Tests for the S&P Connect client, run against the fake server."""

from __future__ import annotations

from datetime import time

import aiohttp
import pytest
from aiohttp.test_utils import TestServer

from custom_components.simpson_partners.api import (
    ChargerState,
    CommandStatus,
    ScheduleWindow,
    SPConnectAuthError,
    SPConnectChargerOfflineError,
    SPConnectClient,
    SPConnectConnectionError,
    SPConnectNotFoundError,
    SPConnectRateLimitError,
    SPConnectResponseError,
)

from .conftest import FixedTokenAuth
from .mock_connect import CHARGER_ID, COMMAND_ID, InjectedError, MockConnectState


async def test_get_chargers(client: SPConnectClient) -> None:
    """Chargers are listed with their details."""
    chargers = await client.async_get_chargers()

    assert len(chargers) == 1
    assert chargers[0].id == CHARGER_ID
    assert chargers[0].serial == "SP0001234"
    assert chargers[0].online is True


async def test_get_charger(client: SPConnectClient) -> None:
    """One charger is fetched by id."""
    charger = await client.async_get_charger(CHARGER_ID)

    assert charger.firmware_version == "3.5.9"


async def test_get_status_with_fault(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """Status carries the state, readings and any active faults."""
    state.status["state"] = "fault"
    state.status["faults"] = [
        {"code": 12, "title": "Earth fault", "message": "Call us", "severity": "high"}
    ]

    status = await client.async_get_status(CHARGER_ID)

    assert status.state is ChargerState.FAULT
    assert status.power_kw == 7.2
    assert status.faults[0].title == "Earth fault"


async def test_get_telemetry_and_sessions(client: SPConnectClient) -> None:
    """Telemetry and sessions are read from their list keys."""
    readings = await client.async_get_telemetry(CHARGER_ID)
    sessions = await client.async_get_sessions(CHARGER_ID)

    assert readings[0].setpoint_a == 32.0
    assert readings[0].solar_kw is None
    assert sessions[0].total_kwh == 21.5


async def test_set_schedule_sends_windows(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """The schedule is sent as HH:MM windows and returns the command."""
    command = await client.async_set_schedule(
        CHARGER_ID, [ScheduleWindow(time(0, 30), time(4, 30))]
    )

    assert command.id == COMMAND_ID
    assert command.status is CommandStatus.SENT
    assert state.received[-1] == (
        "PUT",
        f"/v1/chargers/{CHARGER_ID}/schedule",
        {"windows": [{"start": "00:30", "end": "04:30"}]},
    )


async def test_set_schedule_rejects_too_many_windows(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """More than three windows is refused before any request is sent."""
    window = ScheduleWindow(time(1, 0), time(2, 0))

    with pytest.raises(ValueError, match="At most 3"):
        await client.async_set_schedule(CHARGER_ID, [window] * 4)
    assert state.received == []


async def test_set_current_limit(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """The current limit is sent in amps."""
    command = await client.async_set_current_limit(CHARGER_ID, 16)

    assert command.status is CommandStatus.SENT
    assert state.received[-1][2] == {"amps": 16}


@pytest.mark.parametrize(
    ("method", "path"),
    [("async_start_charging", "start"), ("async_stop_charging", "stop")],
)
async def test_start_and_stop_charging(
    client: SPConnectClient, state: MockConnectState, method: str, path: str
) -> None:
    """Start and stop are bodiless POSTs that return the command."""
    command = await getattr(client, method)(CHARGER_ID)

    assert command.id == COMMAND_ID
    assert state.received[-1] == ("POST", f"/v1/chargers/{CHARGER_ID}/{path}", None)


async def test_stop_refused_for_site_charger(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A charger S&P Connect cannot pause reliably is refused with its code."""
    state.error = InjectedError(
        409, {"error": "control_unavailable", "message": "Managed by a site"}
    )

    with pytest.raises(SPConnectResponseError) as caught:
        await client.async_stop_charging(CHARGER_ID)
    assert caught.value.status == 409
    assert caught.value.code == "control_unavailable"


async def test_get_command(client: SPConnectClient, state: MockConnectState) -> None:
    """A command's delivery state is read back."""
    state.command_status = "acknowledged"

    command = await client.async_get_command(COMMAND_ID)

    assert command.status is CommandStatus.ACKNOWLEDGED


async def test_bad_token_raises_auth_error(
    client: SPConnectClient, auth: FixedTokenAuth
) -> None:
    """A rejected token becomes an auth error, which triggers re-authentication."""
    auth.token = "expired"

    with pytest.raises(SPConnectAuthError, match="401"):
        await client.async_get_chargers()


async def test_unknown_charger_raises_not_found(client: SPConnectClient) -> None:
    """A charger outside this connection is reported as not found."""
    with pytest.raises(SPConnectNotFoundError, match="No such charger"):
        await client.async_get_status("chg_other")


async def test_offline_charger_raises_offline_error(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A 409 charger_offline refusal has its own exception."""
    state.error = InjectedError(
        409, {"error": "charger_offline", "message": "Charger is offline"}
    )

    with pytest.raises(SPConnectChargerOfflineError, match="Charger is offline"):
        await client.async_set_current_limit(CHARGER_ID, 16)


async def test_other_conflict_is_a_response_error(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A 409 for any other reason keeps its status and code."""
    state.error = InjectedError(409, {"error": "busy", "message": "Try later"})

    with pytest.raises(SPConnectResponseError) as caught:
        await client.async_set_current_limit(CHARGER_ID, 16)
    assert caught.value.status == 409
    assert caught.value.code == "busy"


async def test_rate_limit_carries_retry_after(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A 429 reports how long to wait."""
    state.error = InjectedError(
        429, {"error": "rate_limited"}, headers={"Retry-After": "30"}
    )

    with pytest.raises(SPConnectRateLimitError) as caught:
        await client.async_get_chargers()
    assert caught.value.retry_after == 30


async def test_rate_limit_without_retry_after(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A 429 with no usable Retry-After leaves the wait unknown."""
    state.error = InjectedError(429, None, headers={"Retry-After": "soon"})

    with pytest.raises(SPConnectRateLimitError) as caught:
        await client.async_get_chargers()
    assert caught.value.retry_after is None


async def test_server_error_without_body(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A 5xx with an empty body still produces a readable error."""
    state.error = InjectedError(503)

    with pytest.raises(SPConnectResponseError, match="503: no detail"):
        await client.async_get_chargers()


async def test_non_json_error_body(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """An error body that is not an API error object is reported by status."""
    state.error = InjectedError(500, "<html>")

    with pytest.raises(SPConnectResponseError) as caught:
        await client.async_get_chargers()
    assert caught.value.status == 500


async def test_non_json_success_body(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A success response that is not JSON is a response error."""
    state.raw_body = "not json"

    with pytest.raises(SPConnectResponseError, match="not JSON"):
        await client.async_get_chargers()


async def test_malformed_model_is_a_response_error(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A body missing a required field is reported, not half-parsed."""
    state.status = {"power_kw": 1.0}

    with pytest.raises(SPConnectResponseError, match="state is missing"):
        await client.async_get_status(CHARGER_ID)


async def test_missing_list_key_is_a_response_error(
    client: SPConnectClient, state: MockConnectState
) -> None:
    """A list endpoint without its list is reported."""
    state.raw_body = "{}"

    with pytest.raises(SPConnectResponseError, match="chargers is missing"):
        await client.async_get_chargers()


async def test_unreachable_server_raises_connection_error(
    server: TestServer, session: aiohttp.ClientSession, auth: FixedTokenAuth
) -> None:
    """A server that cannot be reached becomes a connection error."""
    url = str(server.make_url("/"))
    await server.close()
    client = SPConnectClient(session, auth, url)

    with pytest.raises(SPConnectConnectionError, match="GET /chargers failed"):
        await client.async_get_chargers()


async def test_timeout_raises_connection_error(
    client: SPConnectClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A request that times out becomes a connection error."""

    def raise_timeout(*_args: object, **_kwargs: object) -> None:
        raise TimeoutError

    monkeypatch.setattr(aiohttp.ClientSession, "request", raise_timeout)

    with pytest.raises(SPConnectConnectionError, match="timed out"):
        await client.async_get_chargers()
