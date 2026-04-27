# Changelog

All notable changes to LogicaHome are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Native Matter adapter via `python-matter-server`.
- Google Home adapter using the official Home APIs.
- REST/SSE surface as an alternative to MCP for non-AI integrators.
- PyPI release with trusted publishing.
- Scenes (multi-device state snapshots) and an MCP `run_scene` tool.
- mDNS / SSDP discovery in `logicahome scan`.

## [0.1.1] - 2026-04-27

### Added

- Interactive `logicahome connect` wizards — no YAML editing required for onboarding.
  - `logicahome connect home-assistant` validates URL + token against `/api/` before saving.
  - `logicahome connect tuya` runs the official tinytuya cloud wizard and imports devices + local keys automatically.
  - `logicahome connect` with no args lists available wizards.
- `logicahome scan` for passive LAN discovery (Tuya UDP broadcast today; mDNS/SSDP planned).
- **Tuya adapter is now functional end-to-end.** Real `tinytuya.OutletDevice` calls for `status()` and `set_multiple_values()`, run inside `asyncio.to_thread` to keep the event loop responsive. Translates DPS values to the canonical `DeviceState` and back, including 0–100 brightness scaling, RGB↔HSV-hex color encoding, and power metering. Per-device DPS overrides supported via `dps_map` in config.
- 7 new pure-function tests for the Tuya helpers (DPS translation, color roundtrip, brightness clamping, error paths). Skipped automatically when the `tuya` extra is not installed.

## [0.1.0] - 2026-04-26

### Added

- Initial project skeleton.
- Core abstractions: `Device`, `DeviceState`, `DeviceCapability`, `Adapter`, `Registry`.
- Persistent device registry backed by SQLite under the user config dir.
- YAML-based user configuration loader.
- `Runtime` orchestrating registry + adapter dispatch, shared by CLI and MCP.
- CLI surface (`logicahome`): `version`, `init`, `discover`, `adapters`, `config`, `device list/on/off/brightness/state`, `mcp serve`, `mcp install`.
- MCP server with seven tools: `list_devices`, `get_state`, `turn_on`, `turn_off`, `set_brightness`, `set_color`, `discover`.
- `mcp install` writes config snippets for Claude Desktop and Cursor.
- Tuya / SmartLife adapter scaffold (config-driven discovery, optional `tinytuya` dep).
- Home Assistant adapter (REST + WebSocket-ready, dynamic discovery via `/api/states`).
- Apache 2.0 license.
- Smoke test suite.

[Unreleased]: https://github.com/Rovemark/logicahome/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/Rovemark/logicahome/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Rovemark/logicahome/releases/tag/v0.1.0
