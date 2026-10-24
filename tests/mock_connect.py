"""A fake S&P Connect /v1 server for tests and local development.

It serves the endpoints the integration uses from in-memory state and can be
told to fail, so tests exercise the real HTTP path rather than a patched
client. Response shapes follow S&P Connect design v1 and must be kept in step
with ``api/models.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aiohttp import web
from aiohttp.typedefs import Handler

VALID_TOKEN = "test-access-token"
CHARGER_ID = "chg_1"
COMMAND_ID = "cmd_1"


@dataclass(slots=True)
class InjectedError:
    """An error response the server returns instead of the normal body."""

    status: int
    body: object = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class MockConnectState:
    """What the fake server returns, and what it has been sent."""

    chargers: list[dict[str, object]] = field(default_factory=list)
    status: dict[str, object] = field(default_factory=dict)
    telemetry: list[dict[str, object]] = field(default_factory=list)
    sessions: list[dict[str, object]] = field(default_factory=list)
    command_status: str = "sent"
    error: InjectedError | None = None
    raw_body: str | None = None
    received: list[tuple[str, str, object]] = field(default_factory=list)


def default_state() -> MockConnectState:
    """Return state for one online charger that is charging."""
    return MockConnectState(
        chargers=[
            {
                "id": CHARGER_ID,
                "serial": "SP0001234",
                "model": "Simpson Home 7",
                "series": "Home",
                "firmware_version": "3.5.9",
                "cable_type": "tethered",
                "online": True,
            }
        ],
        status={
            "state": "charging",
            "power_kw": 7.2,
            "session_kwh": 3.4,
            "last_seen": "2026-10-24T09:00:00+00:00",
            "faults": [],
        },
        telemetry=[
            {
                "recorded_at": "2026-10-24T09:00:00+00:00",
                "power_kw": 7.2,
                "current_a": 31.5,
                "voltage_v": 239.8,
                "setpoint_a": 32,
                "solar_kw": None,
            }
        ],
        sessions=[
            {
                "started_at": "2026-10-23T22:00:00+00:00",
                "ended_at": "2026-10-24T03:00:00+00:00",
                "total_kwh": 21.5,
                "grid_kwh": 21.5,
                "solar_kwh": 0,
            }
        ],
    )


def create_app(state: MockConnectState) -> web.Application:
    """Build the aiohttp application that serves ``state``."""

    @web.middleware
    async def guard(
        request: web.Request,
        handler: Handler,
    ) -> web.StreamResponse:
        """Record the request, then apply auth and any injected failure."""
        body = await request.json() if request.can_read_body else None
        state.received.append((request.method, request.path, body))
        if request.headers.get("Authorization") != f"Bearer {VALID_TOKEN}":
            return _error(401, "invalid_token", "Access token is not valid")
        if state.error is not None:
            err = state.error
            return web.json_response(err.body, status=err.status, headers=err.headers)
        if state.raw_body is not None:
            return web.Response(text=state.raw_body, content_type="application/json")
        return await handler(request)

    def charger_or_404(request: web.Request) -> web.Response | None:
        """Return a 404 response when the charger id is unknown."""
        known = {charger["id"] for charger in state.chargers}
        if request.match_info["charger_id"] not in known:
            return _error(404, "not_found", "No such charger")
        return None

    async def chargers(_: web.Request) -> web.Response:
        return web.json_response({"chargers": state.chargers})

    async def charger(request: web.Request) -> web.Response:
        missing = charger_or_404(request)
        if missing:
            return missing
        found = [
            c for c in state.chargers if c["id"] == request.match_info["charger_id"]
        ]
        return web.json_response(found[0])

    async def status(request: web.Request) -> web.Response:
        return charger_or_404(request) or web.json_response(state.status)

    async def telemetry(request: web.Request) -> web.Response:
        return charger_or_404(request) or web.json_response(
            {"readings": state.telemetry}
        )

    async def sessions(request: web.Request) -> web.Response:
        return charger_or_404(request) or web.json_response(
            {"sessions": state.sessions}
        )

    async def command_accepted(request: web.Request) -> web.Response:
        return charger_or_404(request) or web.json_response(
            {"id": COMMAND_ID, "status": "sent"}, status=202
        )

    async def command(request: web.Request) -> web.Response:
        if request.match_info["command_id"] != COMMAND_ID:
            return _error(404, "not_found", "No such command")
        return web.json_response({"id": COMMAND_ID, "status": state.command_status})

    app = web.Application(middlewares=[guard])
    app.router.add_get("/v1/chargers", chargers)
    app.router.add_get("/v1/chargers/{charger_id}", charger)
    app.router.add_get("/v1/chargers/{charger_id}/status", status)
    app.router.add_get("/v1/chargers/{charger_id}/telemetry", telemetry)
    app.router.add_get("/v1/chargers/{charger_id}/sessions", sessions)
    app.router.add_put("/v1/chargers/{charger_id}/schedule", command_accepted)
    app.router.add_put("/v1/chargers/{charger_id}/current-limit", command_accepted)
    app.router.add_get("/v1/commands/{command_id}", command)
    return app


def _error(status: int, code: str, message: str) -> web.Response:
    """Return an error in S&P Connect's ``{"error", "message"}`` shape."""
    return web.json_response({"error": code, "message": message}, status=status)
