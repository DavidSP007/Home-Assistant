# S&P Connect API used by this integration

S&P Connect is the Simpson & Partners partner gateway. The contract is
`supabase-iot/openapi/connect-v1.yaml` in the SP-Vue repository (version
1.0.0-draft.2, checked against the production code on 7 Nov 2026). The
production host in that file is `https://api.connect.simpson-partners.com`.

Every request sends `Authorization: Bearer <access token>`. Every command also
sends a fresh `Idempotency-Key`, so a retried request is never sent to the
charger twice. Errors are returned as
`{"error": "<code>", "message": "<text>", "request_id": "<id>"}`, and the
client adds the `X-Request-Id` to its error message so an owner can quote it
to support.

Lists the contract marks as extensible (charger state, command status, cable
type, `blocked_by`) can gain values within v1. The client reads a value it does
not know as `unknown` rather than failing. The live gateway already sends state
`unknown` for an offline charger.

| Method | Path | Client method | Returns |
|---|---|---|---|
| GET | `/v1/chargers` | `async_get_chargers` | `{"chargers": [Charger]}` |
| GET | `/v1/chargers/{id}` | `async_get_charger` | `Charger` |
| GET | `/v1/chargers/{id}/status` | `async_get_status` | `ChargerStatus`, including active faults and `blocked_by` |
| POST | `/v1/chargers/{id}/refresh` | `async_refresh` | 202 `Command`; asks the charger to report now (once a minute at most) |
| GET | `/v1/chargers/{id}/telemetry` | `async_get_telemetry` | `{"readings": [TelemetryReading]}` |
| GET | `/v1/chargers/{id}/sessions` | `async_get_sessions` | `{"sessions": [ChargeSession]}` |
| GET | `/v1/chargers/{id}/schedule` | `async_get_schedule` | `Schedule`, as last reported |
| PUT | `/v1/chargers/{id}/schedule` | `async_set_schedule` | 202 `Command`; body `{"windows": [{"start": "HH:MM", "end": "HH:MM"}]}`, at most 3 |
| GET | `/v1/chargers/{id}/current-limit` | `async_get_current_limit` | `CurrentLimit`: the owner's `amps` and the installer's `max_amps` |
| PUT | `/v1/chargers/{id}/current-limit` | `async_set_current_limit` | 202 `Command`; body `{"amps": 16}` |
| POST | `/v1/chargers/{id}/start` | `async_start_charging` | 202 `Command`; no body |
| POST | `/v1/chargers/{id}/stop` | `async_stop_charging` | 202 `Command`; no body |
| GET | `/v1/commands/{id}` | `async_get_command` | `Command` (`sent`, `acknowledged`, `rejected`, `no_reply`), with a plain-English `message` when rejected |

Start and stop resume and pause the charge. S&P Connect refuses a command with
409 when the charger cannot take it now. The reason codes are `user_locked`,
`support_hold`, `charger_in_ocpp_mode`, `controlled_by_partner` and
`managed_by_site` (a legacy site load-balancer controls pause on this charger).

Not used yet: `GET /v1/me`, the `/v1/events` feed, `/v1/connections`, and the
`from`, `to`, `cursor` and `limit` parameters on telemetry and sessions. The
client reads the first page only: the 100 most recent readings or sessions.

## How errors map to exceptions

| Response | Exception |
|---|---|
| 401 | `SPConnectAuthError` |
| 404 | `SPConnectNotFoundError` |
| 409 `charger_offline` | `SPConnectChargerOfflineError` |
| Any other 409 | `SPConnectCommandRefusedError` (with `code`) |
| 429 | `SPConnectRateLimitError` (with `retry_after` seconds) |
| Other 4xx/5xx, or an unreadable body | `SPConnectResponseError` (with `status` and `code`) |
| Network failure or timeout | `SPConnectConnectionError` |

## Limits

120 requests a minute per connection and 10 commands a minute per charger.
Polling `/status` once a minute stays well inside both.
