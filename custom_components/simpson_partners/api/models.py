"""Typed models for S&P Connect /v1 responses and requests.

Field names follow S&P Connect design v1. They are provisional until S&P
Connect publishes its OpenAPI file (build phase 4); all parsing lives here so a
renamed field is a change to this module only.

Each ``from_json`` raises ``ValueError`` on a malformed body; the client turns
that into ``SPConnectResponseError``. Lists the contract marks extensible (state,
command status, cable type, blocked-by) may gain values inside v1, so an
unrecognised value parses as ``UNKNOWN`` instead of failing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum

from .parsing import (
    JsonObject,
    as_object,
    get_bool,
    get_datetime,
    get_float,
    get_int,
    get_optional_datetime,
    get_optional_float,
    get_optional_str,
    get_str,
)

_LOGGER = logging.getLogger(__name__)


def _extensible[E: StrEnum](enum: type[E], value: str, unknown: E) -> E:
    """Return the member for value, or ``unknown`` for one added after this release."""
    try:
        return enum(value)
    except ValueError:
        _LOGGER.debug(
            "Unrecognised %s value %r treated as unknown", enum.__name__, value
        )
        return unknown


class ChargerState(StrEnum):
    """Charging state reported by /status."""

    IDLE = "idle"
    CHARGING = "charging"
    PAUSED = "paused"
    FAULT = "fault"
    UNKNOWN = "unknown"


class CommandStatus(StrEnum):
    """Delivery state of a command, from /commands/{id}."""

    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    NO_REPLY = "no_reply"
    UNKNOWN = "unknown"


class CableType(StrEnum):
    """Whether the charger has a fixed cable or a socket."""

    TETHERED = "tethered"
    SOCKET = "socket"
    UNKNOWN = "unknown"


class BlockedBy(StrEnum):
    """Why S&P Connect would refuse commands right now (from /status)."""

    SUPPORT_HOLD = "support_hold"
    OCPP_PROVIDER = "ocpp_provider"
    UNKNOWN = "unknown"


@dataclass(slots=True, frozen=True)
class Charger:
    """A charger on this connection (GET /v1/chargers/{id})."""

    id: str
    serial: str
    model: str | None
    series: str | None
    firmware_version: str | None
    cable_type: CableType | None
    online: bool

    @classmethod
    def from_json(cls, data: JsonObject) -> Charger:
        """Build a charger from its JSON object."""
        cable = get_optional_str(data, "cable_type")
        return cls(
            id=get_str(data, "id"),
            serial=get_str(data, "serial"),
            model=get_optional_str(data, "model"),
            series=get_optional_str(data, "series"),
            firmware_version=get_optional_str(data, "firmware_version"),
            cable_type=(
                _extensible(CableType, cable, CableType.UNKNOWN)
                if cable is not None
                else None
            ),
            online=get_bool(data, "online"),
        )


@dataclass(slots=True, frozen=True)
class Fault:
    """An active fault, worded for the charger's owner. ``code`` may be absent."""

    code: int | None
    title: str
    message: str
    severity: str

    @classmethod
    def from_json(cls, data: JsonObject) -> Fault:
        """Build a fault from its JSON object."""
        return cls(
            code=None if data.get("code") is None else get_int(data, "code"),
            title=get_str(data, "title"),
            message=get_str(data, "message"),
            severity=get_str(data, "severity"),
        )


@dataclass(slots=True, frozen=True)
class ChargerStatus:
    """Live status (GET /v1/chargers/{id}/status). None means "not reported"."""

    state: ChargerState
    power_kw: float | None
    session_kwh: float | None
    last_seen: datetime | None
    blocked_by: BlockedBy | None
    faults: tuple[Fault, ...]

    @classmethod
    def from_json(cls, data: JsonObject) -> ChargerStatus:
        """Build a status from its JSON object."""
        faults = data.get("faults", [])
        if not isinstance(faults, list):
            raise ValueError("faults is not a list")
        blocked = get_optional_str(data, "blocked_by")
        return cls(
            state=_extensible(
                ChargerState, get_str(data, "state"), ChargerState.UNKNOWN
            ),
            power_kw=get_optional_float(data, "power_kw"),
            session_kwh=get_optional_float(data, "session_kwh"),
            last_seen=get_optional_datetime(data, "last_seen"),
            blocked_by=(
                _extensible(BlockedBy, blocked, BlockedBy.UNKNOWN)
                if blocked is not None
                else None
            ),
            faults=tuple(Fault.from_json(as_object(item)) for item in faults),
        )


@dataclass(slots=True, frozen=True)
class TelemetryReading:
    """One 1-minute reading (GET /v1/chargers/{id}/telemetry)."""

    recorded_at: datetime
    power_kw: float | None
    current_a: float | None
    voltage_v: float | None
    setpoint_a: float | None
    solar_kw: float | None

    @classmethod
    def from_json(cls, data: JsonObject) -> TelemetryReading:
        """Build a reading from its JSON object."""
        return cls(
            recorded_at=get_datetime(data, "recorded_at"),
            power_kw=get_optional_float(data, "power_kw"),
            current_a=get_optional_float(data, "current_a"),
            voltage_v=get_optional_float(data, "voltage_v"),
            setpoint_a=get_optional_float(data, "setpoint_a"),
            solar_kw=get_optional_float(data, "solar_kw"),
        )


@dataclass(slots=True, frozen=True)
class ChargeSession:
    """A completed charge (GET /v1/chargers/{id}/sessions)."""

    started_at: datetime
    ended_at: datetime
    total_kwh: float
    grid_kwh: float | None
    solar_kwh: float | None

    @classmethod
    def from_json(cls, data: JsonObject) -> ChargeSession:
        """Build a session from its JSON object."""
        return cls(
            started_at=get_datetime(data, "started_at"),
            ended_at=get_datetime(data, "ended_at"),
            total_kwh=get_float(data, "total_kwh"),
            grid_kwh=get_optional_float(data, "grid_kwh"),
            solar_kwh=get_optional_float(data, "solar_kwh"),
        )


@dataclass(slots=True, frozen=True)
class Command:
    """A command sent to the charger and its delivery state.

    ``message`` is S&P Connect's plain-English reason when the charger rejected it.
    """

    id: str
    status: CommandStatus
    message: str | None

    @classmethod
    def from_json(cls, data: JsonObject) -> Command:
        """Build a command from its JSON object."""
        return cls(
            id=get_str(data, "id"),
            status=_extensible(
                CommandStatus, get_str(data, "status"), CommandStatus.UNKNOWN
            ),
            message=get_optional_str(data, "message"),
        )


@dataclass(slots=True, frozen=True)
class CurrentLimit:
    """The owner's current limit and the installer's maximum, in amps."""

    amps: int | None
    max_amps: int | None

    @classmethod
    def from_json(cls, data: JsonObject) -> CurrentLimit:
        """Build a current limit from its JSON object."""
        return cls(
            amps=None if data.get("amps") is None else get_int(data, "amps"),
            max_amps=(
                None if data.get("max_amps") is None else get_int(data, "max_amps")
            ),
        )


@dataclass(slots=True, frozen=True)
class ScheduleWindow:
    """One charging window, in the charger's local time."""

    start: time
    end: time

    @classmethod
    def from_json(cls, data: JsonObject) -> ScheduleWindow:
        """Build a window from {"start": "HH:MM", "end": "HH:MM"}."""
        return cls(
            start=time.fromisoformat(get_str(data, "start")),
            end=time.fromisoformat(get_str(data, "end")),
        )

    def to_json(self) -> JsonObject:
        """Serialise as {"start": "HH:MM", "end": "HH:MM"}."""
        return {
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
        }


@dataclass(slots=True, frozen=True)
class Schedule:
    """The charging schedule as the charger last reported it."""

    windows: tuple[ScheduleWindow, ...]

    @classmethod
    def from_json(cls, data: JsonObject) -> Schedule:
        """Build a schedule from its JSON object."""
        windows = data.get("windows")
        if not isinstance(windows, list):
            raise ValueError("windows is missing or not a list")
        return cls(
            windows=tuple(ScheduleWindow.from_json(as_object(w)) for w in windows)
        )
