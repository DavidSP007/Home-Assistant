"""Constants for the Simpson & Partners integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "simpson_partners"
NAME: Final = "Simpson & Partners"

# S&P Connect /v1 API, host as published in connect-v1.yaml (servers: Production).
# The client always takes the base URL as a parameter, so a change of host is a
# change to this line only.
DEFAULT_API_BASE_URL: Final = "https://api.connect.simpson-partners.com"
API_VERSION_PATH: Final = "/v1"

REQUEST_TIMEOUT_SECONDS: Final = 10

# Endpoint paths, relative to the /v1 root.
PATH_CHARGERS: Final = "/chargers"
PATH_CHARGER: Final = "/chargers/{charger_id}"
PATH_STATUS: Final = "/chargers/{charger_id}/status"
PATH_TELEMETRY: Final = "/chargers/{charger_id}/telemetry"
PATH_SESSIONS: Final = "/chargers/{charger_id}/sessions"
PATH_SCHEDULE: Final = "/chargers/{charger_id}/schedule"
PATH_CURRENT_LIMIT: Final = "/chargers/{charger_id}/current-limit"
PATH_REFRESH: Final = "/chargers/{charger_id}/refresh"
PATH_START: Final = "/chargers/{charger_id}/start"
PATH_STOP: Final = "/chargers/{charger_id}/stop"
PATH_COMMAND: Final = "/commands/{command_id}"

# S&P Connect allows at most 3 schedule windows (firmware setSched limit).
MAX_SCHEDULE_WINDOWS: Final = 3

# Commands carry an Idempotency-Key so a retried request never sends twice.
HEADER_IDEMPOTENCY_KEY: Final = "Idempotency-Key"
HEADER_REQUEST_ID: Final = "X-Request-Id"
