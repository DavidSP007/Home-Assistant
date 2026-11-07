"""S&P Connect API client: the integration's only route to the charger cloud."""

from .auth import AbstractAuth
from .client import SPConnectClient
from .exceptions import (
    SPConnectAuthError,
    SPConnectChargerOfflineError,
    SPConnectCommandRefusedError,
    SPConnectConnectionError,
    SPConnectError,
    SPConnectNotFoundError,
    SPConnectRateLimitError,
    SPConnectResponseError,
)
from .models import (
    BlockedBy,
    CableType,
    Charger,
    ChargerState,
    ChargerStatus,
    ChargeSession,
    Command,
    CommandStatus,
    CurrentLimit,
    Fault,
    Schedule,
    ScheduleWindow,
    TelemetryReading,
)

__all__ = [
    "AbstractAuth",
    "BlockedBy",
    "CableType",
    "ChargeSession",
    "Charger",
    "ChargerState",
    "ChargerStatus",
    "Command",
    "CommandStatus",
    "CurrentLimit",
    "Fault",
    "SPConnectAuthError",
    "SPConnectChargerOfflineError",
    "SPConnectClient",
    "SPConnectCommandRefusedError",
    "SPConnectConnectionError",
    "SPConnectError",
    "SPConnectNotFoundError",
    "SPConnectRateLimitError",
    "SPConnectResponseError",
    "Schedule",
    "ScheduleWindow",
    "TelemetryReading",
]
