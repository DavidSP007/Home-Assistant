# S&P Connect API used by this integration

S&P Connect is the Simpson & Partners partner gateway. Field names below
follow S&P Connect design v1 and are provisional until its OpenAPI file is
published.

Every request sends `Authorization: Bearer <access token>`. Errors are
returned as `{"error": "<code>", "message": "<text>"}`.

| Method | Path | Client method | Returns |
|---|---|---|---|
| GET | `/v1/chargers` | `async_get_chargers` | `{"chargers": [Charger]}` |
| GET | `/v1/chargers/{id}` | `async_get_charger` | `Charger` |
| GET | `/v1/chargers/{id}/status` | `async_get_status` | `ChargerStatus`, including active faults |
| GET | `/v1/chargers/{id}/telemetry` | `async_get_telemetry` | `{"readings": [TelemetryReading]}` |
| GET | `/v1/chargers/{id}/sessions` | `async_get_sessions` | `{"sessions": [ChargeSession]}` |
| PUT | `/v1/chargers/{id}/schedule` | `async_set_schedule` | 202 `Command`; body `{"windows": [{"start": "HH:MM", "end": "HH:MM"}]}`, at most 3 |
| PUT | `/v1/chargers/{id}/current-limit` | `async_set_current_limit` | 202 `Command`; body `{"amps": 16}` |
| POST | `/v1/chargers/{id}/start` | `async_start_charging` | 202 `Command`; no body |
| POST | `/v1/chargers/{id}/stop` | `async_stop_charging` | 202 `Command`; no body |
| GET | `/v1/commands/{id}` | `async_get_command` | `Command` (`sent`, `acknowledged`, `rejected`, `no_reply`) |

Start and stop resume and pause the charge. S&P Connect refuses them with
409 (a code other than `charger_offline`) for chargers it cannot pause
reliably: those attached to a business site on the legacy server, and those
running OCPP. The client reports that as `SPConnectResponseError` with the code.

## How errors map to exceptions

| Response | Exception |
|---|---|
| 401 | `SPConnectAuthError` |
| 404 | `SPConnectNotFoundError` |
| 409 `charger_offline` | `SPConnectChargerOfflineError` |
| 429 | `SPConnectRateLimitError` (with `retry_after` seconds) |
| Other 4xx/5xx, or an unreadable body | `SPConnectResponseError` (with `status` and `code`) |
| Network failure or timeout | `SPConnectConnectionError` |

## Limits

120 requests a minute per connection and 10 commands a minute per charger.
Polling `/status` once a minute stays well inside both.
