# Architecture

## The path from Home Assistant to a charger

```text
Home Assistant ──HTTPS, OAuth──▶ S&P Connect /v1 ──▶ IoT platform ──MQTT──▶ charger
```

The integration only talks to **S&P Connect**. S&P Connect checks the token,
applies rate limits and turns each request into a firmware command, so the
integration never sees MQTT, firmware commands or Simpson & Partners'
internal databases.

## Layers

| Layer | Module | Job | Status |
|---|---|---|---|
| API client | `api/` | Talks HTTP to S&P Connect, returns typed models, raises typed errors | This release |
| Sign-in | `config_flow.py`, `application_credentials.py` | OAuth 2.1 with PKCE through Home Assistant's account linking | Next |
| Coordinator | `coordinator.py` | Polls `/status` about every 60 seconds and shares it with entities | Next |
| Entities | `sensor.py`, `switch.py`, `binary_sensor.py`, … | What the user sees and controls | Later |
| Support | `diagnostics.py`, `repairs.py` | Diagnostics download and repair prompts | Later |

## Decisions in this release

- **The client depends on an abstract token provider** (`api/auth.py`). The
  sign-in release supplies one backed by Home Assistant's OAuth session; tests
  supply a fixed token. The client never handles refresh tokens itself.
- **`api/` imports nothing from Home Assistant.** Home Assistant core requires
  the API code in a separate library, so it is written to move out unchanged.
- **One exception type per failure the caller acts on differently**: sign-in
  rejected (start re-authentication), charger offline, not found, rate
  limited (with the wait time), unreachable, and anything else unexpected.
  Callers never read error text to decide what to do.
- **Strict parsing.** A response missing a required field raises an error
  instead of producing a half-filled model. All field names live in
  `api/models.py`, because S&P Connect has not yet published its final
  OpenAPI file and some names may change.
- **Start and stop pause and resume the charge.** S&P Connect sends the
  firmware's `control` command with only its pause flag. Chargers attached to
  a business site on the legacy server are refused, because that server undoes
  a pause on every telemetry message; home chargers are unaffected.
- **Tests run against a mock S&P Connect server** (`tests/components/simpson_partners/mock_connect.py`)
  over real HTTP, so they exercise the same path as production.

## Distribution

Shipped through HACS first, laid out to Home Assistant core's rules so it can
move into core later: platform files at the top of the integration folder,
tests outside it.
