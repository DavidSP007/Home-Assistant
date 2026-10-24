"""S&P Connect API client: the integration's only route to the charger cloud."""

from .auth import AbstractAuth
from .client import SPConnectClient
from .exceptions import (
    SPConnectAuthError,
    SPConnectChargerOfflineError,
    SPConnectConnectionError,
    SPConnectError,
    SPConnectNotFoundError,
    SPConnectRateLimitError,
    SPConnectResponseError,
)
from .models import (
    CableType,
    Charger,
    ChargerState,
    ChargerStatus,
    ChargeSession,
    Command,
    CommandStatus,
    Fault,
    ScheduleWindow,
    TelemetryReading,
)

__all__ = [
    "AbstractAuth",
    "CableType",
    "ChargeSession",
    "Charger",
    "ChargerState",
    "ChargerStatus",
    "Command",
    "CommandStatus",
    "Fault",
    "SPConnectAuthError",
    "SPConnectChargerOfflineError",
    "SPConnectClient",
    "SPConnectConnectionError",
    "SPConnectError",
    "SPConnectNotFoundError",
    "SPConnectRateLimitError",
    "SPConnectResponseError",
    "ScheduleWindow",
    "TelemetryReading",
]
