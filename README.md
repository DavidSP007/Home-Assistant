# Simpson & Partners for Home Assistant

A Home Assistant integration for Simpson & Partners EV chargers. It connects
through **S&P Connect**, the Simpson & Partners partner API, and does not use
the gateway that energy suppliers use.

## Status

Early development. This release contains the S&P Connect API client, a mock
S&P Connect server and their tests. Sign-in, devices and entities follow in
the next releases. The integration cannot be added to Home Assistant yet.

## What it will do

- Sign in with your Simpson & Partners account, or as a guest with the
  charger's serial number and PIN.
- Show charging state, power, energy, faults and recent charges.
- Let you lock the charger, boost a charge, set the current limit and set up
  to three charging windows.
- Start and stop charging, once the charger firmware supports it.

## Installation (when released)

Install through [HACS](https://hacs.xyz) as a custom repository, then add
**Simpson & Partners** from Settings, Devices & services.

## Documentation

- [Architecture.md](Architecture.md): how the integration is built.
- [API.md](API.md): the S&P Connect endpoints it uses.
- [Development.md](Development.md): how to run the checks and tests.
- [Changelog.md](Changelog.md): what changed in each release.
