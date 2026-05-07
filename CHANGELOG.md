# Changelog

All notable changes to LogicaHome are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0](https://github.com/Rovemark/logicahome/compare/v0.4.0...v0.5.0) (2026-05-07)


### Features

* **web:** config + pairing endpoints for visual onboarding ([2497d61](https://github.com/Rovemark/logicahome/commit/2497d610cc5cb13d923cfdb640595b8729a65c5a))
* **web:** HA mDNS detect + Tuya Cloud auto-discovery ([e21ab9a](https://github.com/Rovemark/logicahome/commit/e21ab9a9c25ea682a5b17486ec5e94044d478296))

## [Unreleased]

### Planned

- Full Matter adapter implementation against `python-matter-server`.
- Google Home adapter using the official Home APIs.
- Per-user memory ("Andre likes the living room at 60% before bed").

## [0.4.0] - 2026-05-06

### Added

- **Web dashboard** at `logicahome ui` (Starlette + Jinja2 + htmx + Pico CSS, zero npm).
  - Pages: Overview, Devices (live state polling), Scenes (snapshot + run), Connect, Scan, Settings.
  - Auto-opens the browser to `http://127.0.0.1:8765` by default.
  - Same port serves HTML, JSON API, and the MCP SSE endpoint at `/sse`.
- **Public JSON API** for any external dashboard or automation tool:
  - `GET /api/health` `/api/version` `/api/adapters`
  - `GET /api/devices` `/api/devices/{slug}`
  - `POST /api/devices/{slug}/state`
  - `GET/POST /api/scenes` `POST /api/scenes/{slug}/run` `DELETE /api/scenes/{slug}` `POST /api/scenes/snapshot`
  - `POST /api/discover` `GET /api/scan`
- Wheel packaging now bundles `web/templates/` so `logicahome ui` works after `pip install logicahome`.

[0.4.0]: https://github.com/Rovemark/logicahome/compare/v0.3.0...v0.4.0

## [0.3.0] - 2026-05-06

### Added

- Six adapters total: Tuya, Home Assistant, Philips Hue, Shelly (Gen1+Gen2), ESPHome, Matter (skeleton).
- `logicahome connect hue` and `logicahome connect shelly` wizards.
- MCP HTTP/SSE transport — `logicahome mcp serve --http` exposes the same surface to remote clients.
- mDNS / zeroconf discovery in `logicahome scan` for Hue/HomeKit/ESPHome/Matter/Shelly.
- Structured errors with stable codes; the MCP server returns them instead of raw tracebacks.
- Configurable timeout via `LOGICAHOME_TIMEOUT_S`.
- Structured logging via `LOGICAHOME_LOG_LEVEL` (stderr only — keeps MCP stdio clean).
- Schema versioning + automatic migrations on registry initialize.
- Expanded device capabilities (climate, lock, cover, fan, media, battery) and matching `DeviceState` fields.
- Home Assistant full coverage: climate, lock, cover, media_player, fan.
- Light-touch i18n via `LOGICAHOME_LANG`.
- CLI auto-completion enabled.
- Dockerfile + `.dockerignore` for headless deployments.
- systemd service file at `packaging/logicahome.service`.
- MkDocs Material doc-site config.
- Hardware testing checklist and demo recording script.
- Release Please workflow for automated changelog PRs.
- CodeQL security scanning workflow.
- `.github/FUNDING.yml`.
- Pre-commit hooks (`.pre-commit-config.yaml`).

### Changed

- CI caches pip and reports coverage to Codecov for the canonical job.
- All third-party deps now have upper bounds.

[0.3.0]: https://github.com/Rovemark/logicahome/compare/v0.2.0...v0.3.0

## [0.2.0] - 2026-04-27

### Added

- **Scenes** — multi-device state snapshots that any AI can trigger by name.
  - New `Scene` and `SceneAction` models in `logicahome.core.scene`.
  - SQLite persistence (new `scenes` table; existing registries auto-migrate on startup).
  - Three new MCP tools: `list_scenes`, `run_scene(slug)`, `snapshot_scene(slug, name, description?)`.
  - `run_scene` fans device updates out concurrently and reports a per-device status map; one device failure no longer aborts the rest of the scene.
  - `snapshot_scene` reads the current state of every known device and saves it as a reusable scene — perfect for "save this as bedtime".
  - New CLI subcommand: `logicahome scene list | run | snapshot | remove`.
- New cookbook with prompt patterns and CLI recipes: [`docs/cookbook.md`](docs/cookbook.md).
- README links to the cookbook and reflects the expanded MCP surface (10 tools).

### Changed

- `Runtime` now exposes `list_scenes`, `save_scene`, `remove_scene`, `run_scene`, and `snapshot_scene`. CLI and MCP server both consume them — no behavior split between surfaces.

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

[Unreleased]: https://github.com/Rovemark/logicahome/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Rovemark/logicahome/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/Rovemark/logicahome/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Rovemark/logicahome/releases/tag/v0.1.0
