"""Tests for parsing S&P Connect JSON into typed models."""

from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

from custom_components.simpson_partners.api import (
    BlockedBy,
    CableType,
    Charger,
    ChargerState,
    ChargerStatus,
    Command,
    CommandStatus,
    CurrentLimit,
    Schedule,
    ScheduleWindow,
)
from custom_components.simpson_partners.api.parsing import (
    as_object,
    get_bool,
    get_datetime,
    get_float,
    get_int,
    get_optional_str,
)


def test_charger_optional_fields_may_be_null() -> None:
    """A charger with only the required fields parses."""
    charger = Charger.from_json(
        {"id": "c", "serial": "S", "online": False, "cable_type": None}
    )

    assert charger.model is None
    assert charger.cable_type is None


def test_charger_cable_type() -> None:
    """A known cable type maps to the enum."""
    charger = Charger.from_json(
        {"id": "c", "serial": "S", "online": True, "cable_type": "socket"}
    )

    assert charger.cable_type is CableType.SOCKET


def test_unknown_state_is_unknown() -> None:
    """S&P Connect sends "unknown" for an offline charger, and may add states later."""
    assert ChargerStatus.from_json({"state": "unknown"}).state is ChargerState.UNKNOWN
    assert ChargerStatus.from_json({"state": "boosting"}).state is ChargerState.UNKNOWN


def test_unknown_extensible_values_are_unknown() -> None:
    """Every list the contract marks extensible tolerates new values."""
    charger = Charger.from_json(
        {"id": "c", "serial": "S", "online": True, "cable_type": "wireless"}
    )
    command = Command.from_json({"id": "x", "status": "queued"})
    status = ChargerStatus.from_json({"state": "idle", "blocked_by": "maintenance"})

    assert charger.cable_type is CableType.UNKNOWN
    assert command.status is CommandStatus.UNKNOWN
    assert status.blocked_by is BlockedBy.UNKNOWN


def test_status_blocked_by_and_fault_without_code() -> None:
    """A support hold is reported, and a fault may have no code."""
    status = ChargerStatus.from_json(
        {
            "state": "fault",
            "blocked_by": "support_hold",
            "faults": [
                {"code": None, "title": "Fault", "message": "Call us", "severity": "x"}
            ],
        }
    )

    assert status.blocked_by is BlockedBy.SUPPORT_HOLD
    assert status.faults[0].code is None


def test_schedule_requires_windows_list() -> None:
    """A schedule without its windows list is rejected."""
    with pytest.raises(ValueError, match="windows is missing"):
        Schedule.from_json({})


def test_current_limit_may_be_unreported() -> None:
    """Both limits may be null until the charger reports them."""
    limit = CurrentLimit.from_json({"amps": None, "max_amps": None})

    assert limit.amps is None
    assert limit.max_amps is None


def test_status_defaults_to_no_faults() -> None:
    """A status with no faults key has an empty fault list."""
    status = ChargerStatus.from_json({"state": "idle"})

    assert status.faults == ()
    assert status.last_seen is None


def test_status_faults_must_be_a_list() -> None:
    """A faults value that is not a list is rejected."""
    with pytest.raises(ValueError, match="faults is not a list"):
        ChargerStatus.from_json({"state": "idle", "faults": {}})


def test_command_parses() -> None:
    """A command keeps its id and status."""
    assert Command.from_json({"id": "x", "status": "no_reply"}).id == "x"


def test_schedule_window_serialises_as_hh_mm() -> None:
    """Schedule windows are sent without seconds."""
    window = ScheduleWindow(time(7, 5, 59), time(23, 0))

    assert window.to_json() == {"start": "07:05", "end": "23:00"}


def test_as_object_rejects_non_objects() -> None:
    """Only JSON objects are accepted where an object is expected."""
    with pytest.raises(ValueError, match="expected a JSON object"):
        as_object([1, 2])


@pytest.mark.parametrize("value", [True, "1", None])
def test_get_int_rejects_non_integers(value: object) -> None:
    """Booleans, strings and nulls are not integers."""
    with pytest.raises(ValueError, match="n is missing or not an integer"):
        get_int({"n": value}, "n")


def test_get_float_rejects_booleans_and_accepts_ints() -> None:
    """A JSON integer is a valid number; a boolean is not."""
    assert get_float({"n": 3}, "n") == 3.0
    with pytest.raises(ValueError, match="not a number"):
        get_float({"n": True}, "n")


def test_get_optional_str_rejects_wrong_type() -> None:
    """An optional string that is present must still be a string."""
    with pytest.raises(ValueError, match="not a string"):
        get_optional_str({"s": 5}, "s")


def test_get_datetime_requires_time_zone() -> None:
    """Timestamps without a time zone are rejected."""
    assert get_datetime({"t": "2026-10-24T09:00:00Z"}, "t") == datetime(
        2026, 10, 24, 9, 0, tzinfo=UTC
    )
    with pytest.raises(ValueError, match="t has no time zone"):
        get_datetime({"t": "2026-10-24T09:00:00"}, "t")


def test_get_bool_rejects_non_booleans() -> None:
    """A truthy string is not a boolean."""
    with pytest.raises(ValueError, match="online is missing or not a boolean"):
        get_bool({"online": "yes"}, "online")
