"""Typed models for S&P Connect /v1 responses and requests.

Field names follow S&P Connect design v1. They are provisional until S&P
Connect publishes its OpenAPI file (build phase 4); all parsing lives here so a
renamed field is a change to this module only.

Each ``from_json`` raises ``ValueError`` on a malformed body; the client turns
that into ``SPConnectResponseError``.
"""

from __future__ import annotations

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


class ChargerState(StrEnum):
    """Charging state reported by /status."""

    IDLE = "idle"
    CHARGING = "charging"
    PAUSED = "paused"
    FAULT = "fault"


class CommandStatus(StrEnum):
    """Delivery state of a command, from /commands/{id}."""

    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    NO_REPLY = "no_reply"


class CableType(StrEnum):
    """Whether the charger has a fixed cable or a socket."""

    TETHERED = "tethered"
    SOCKET = "socket"


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
            cable_type=CableType(cable) if cable is not None else None,
            online=get_bool(data, "online"),
        )


@dataclass(slots=True, frozen=True)
class Fault:
    """An active fault, worded for the charger's owner."""

    code: int
    title: str
    message: str
    severity: str

    @classmethod
    def from_json(cls, data: JsonObject) -> Fault:
        """Build a fault from its JSON object."""
        return cls(
            code=get_int(data, "code"),
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
    faults: tuple[Fault, ...]

    @classmethod
    def from_json(cls, data: JsonObject) -> ChargerStatus:
        """Build a status from its JSON object."""
        faults = data.get("faults", [])
        if not isinstance(faults, list):
            raise ValueError("faults is not a list")
        return cls(
            state=ChargerState(get_str(data, "state")),
            power_kw=get_optional_float(data, "power_kw"),
            session_kwh=get_optional_float(data, "session_kwh"),
            last_seen=get_optional_datetime(data, "last_seen"),
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
    """A command sent to the charger and its delivery state."""

    id: str
    status: CommandStatus

    @classmethod
    def from_json(cls, data: JsonObject) -> Command:
        """Build a command from its JSON object."""
        return cls(
            id=get_str(data, "id"), status=CommandStatus(get_str(data, "status"))
        )


@dataclass(slots=True, frozen=True)
class ScheduleWindow:
    """One charging window, in the charger's local time."""

    start: time
    end: time

    def to_json(self) -> JsonObject:
        """Serialise as {"start": "HH:MM", "end": "HH:MM"}."""
        return {
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
        }
