<h1 align="center">LogicaHome</h1>

<p align="center">
  <strong>Local-first MCP server and CLI for smart home control.</strong><br/>
  Plug any AI into your home — Claude Desktop, Antigravity, Cursor, ChatGPT, local LLMs.
</p>

<p align="center">
  <a href="https://github.com/Rovemark/logicahome/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Rovemark/logicahome/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/Rovemark/logicahome/blob/main/LICENSE"><img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache%202.0-blue.svg"></a>
  <a href="https://www.python.org/downloads/"><img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-blue.svg"></a>
  <a href="https://modelcontextprotocol.io"><img alt="MCP" src="https://img.shields.io/badge/protocol-MCP-7d3aed.svg"></a>
  <a href="https://github.com/Rovemark/logicahome/blob/main/CONTRIBUTING.md"><img alt="PRs welcome" src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg"></a>
</p>

---

LogicaHome is an open-source bridge between any large language model and the devices in your home. It runs on your local network, exposes a clean [Model Context Protocol](https://modelcontextprotocol.io) interface, and ships with adapters for the most common smart-home ecosystems.

You bring the AI. LogicaHome handles the lights.

## Table of contents

- [Why](#why)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Supported adapters](#supported-adapters)
- [CLI reference](#cli-reference)
- [MCP tools](#mcp-tools)
- [Configuration](#configuration)
- [Development](#development)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

## Why

Smart home today is fragmented. Each ecosystem (Tuya/SmartLife, Google Home, Apple Home, Home Assistant, Matter) speaks its own protocol. Each AI assistant has its own integration story. Most setups push your data to a vendor cloud you do not control.

LogicaHome takes the opposite stance:

- **Local-first.** The daemon runs on your machine. No mandatory cloud.
- **AI-agnostic.** Speaks MCP. Any client that speaks MCP works.
- **Vendor-agnostic.** One adapter per ecosystem. Add yours in a single file.
- **Open.** Apache 2.0. No paid core. Community-owned.

## Quick start

Install:

```bash
pip install logicahome
# or, with Tuya support:
pip install "logicahome[tuya]"
```

Connect your devices using a guided wizard (no YAML editing required):

```bash
logicahome init                       # creates the config file
logicahome connect                    # lists available wizards
logicahome connect home-assistant     # paste URL + token, auto-validated
logicahome connect tuya               # runs the tinytuya cloud wizard once
logicahome discover                   # imports devices into the registry
```

Then install as an MCP server in Claude Desktop:

```bash
logicahome mcp install --client claude
```

Restart Claude Desktop. Ask it to *"turn the living room light to 30%"* and it will pick the right tool.

Prefer the terminal? Same surface:

```bash
logicahome device list
logicahome device on living-room-lamp
logicahome device brightness living-room-lamp 30
logicahome device state living-room-lamp
```

## Connecting devices

LogicaHome ships an interactive wizard for every adapter that needs setup. You should never have to hand-edit YAML.

| Wizard | What it does |
|---|---|
| `logicahome connect home-assistant` | Asks for HA URL + long-lived token, validates against `/api/`, saves config |
| `logicahome connect tuya` | Runs the official tinytuya cloud wizard once, imports devices + local keys |
| `logicahome scan` | Passive LAN scan (Tuya UDP broadcast today; mDNS/SSDP planned) |

After running a wizard, run `logicahome discover` to populate the device registry. The MCP server picks the new devices up automatically — no restart needed for new clients.

If your ecosystem isn't listed, [request an adapter](https://github.com/Rovemark/logicahome/issues/new?template=adapter_request.yml).

## How it works

```
   Any MCP client
   (Claude Desktop, Antigravity, Cursor, ChatGPT, ...)
              │
              │  MCP (stdio or SSE)
              ▼
   ┌────────────────────────────┐
   │   LogicaHome MCP server    │
   │   (runs on your machine)   │
   └─────────────┬──────────────┘
                 │
       ┌─────────┼──────────┐
       ▼         ▼          ▼
     Tuya    Home        Matter
     LAN     Assistant   (planned)
```

The server keeps a small SQLite registry of discovered devices and routes tool calls to the right adapter. Each adapter is a Python class that implements four methods. Writing one is the smallest unit of contribution — see [`docs/writing-adapters.md`](docs/writing-adapters.md).

The same `Runtime` powers the MCP server and the CLI, so anything you can do from one surface, you can do from the other.

## Supported adapters

| Adapter | Status | Protocol | Notes |
|---|---|---|---|
| Tuya / SmartLife | beta | local LAN (no cloud required) | needs `tinytuya` extra |
| Home Assistant | beta | REST | bridges into an existing HA install |
| Google Home | planned | Home APIs | requires Google Cloud project |
| Matter | planned | native Matter controller | via `python-matter-server` |
| Apple HomeKit | planned | HAP | macOS host recommended |
| Philips Hue | planned | local LAN |  |
| Shelly | planned | local LAN / MQTT |  |

Want one that isn't here? Open an [adapter request](https://github.com/Rovemark/logicahome/issues/new?template=adapter_request.yml) — or write it yourself.

## CLI reference

```text
logicahome version                          # print version
logicahome init                             # create config
logicahome discover                         # scan adapters and update registry
logicahome adapters                         # list bundled adapters
logicahome config                           # print resolved config

logicahome device list                      # list known devices
logicahome device state <slug>              # print current state
logicahome device on <slug>                 # turn on
logicahome device off <slug>                # turn off
logicahome device brightness <slug> <0-100> # set brightness

logicahome mcp serve                        # run MCP server over stdio
logicahome mcp install --client claude      # install in Claude Desktop
logicahome mcp install --client cursor      # install in Cursor
logicahome mcp install --client print       # print config snippet
```

## MCP tools

The MCP server exposes seven tools. Schemas are defined in [`src/logicahome/server.py`](src/logicahome/server.py):

| Tool | Purpose |
|---|---|
| `list_devices` | List every device known to LogicaHome. |
| `get_state` | Get the current state of a device by slug. |
| `turn_on` | Turn a device on (optionally set brightness). |
| `turn_off` | Turn a device off. |
| `set_brightness` | Set brightness 0–100 (implies on). |
| `set_color` | Set RGB color (each channel 0–255). |
| `discover` | Re-scan all configured adapters. |

## Configuration

LogicaHome reads its config from a YAML file under the platform-specific user config directory:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/logicahome/config.yaml` |
| Linux | `~/.config/logicahome/config.yaml` |
| Windows | `%APPDATA%\logicahome\config.yaml` |

A starter file is at [`examples/config.yaml`](examples/config.yaml). Adapter-specific config goes under `adapters:`. Run `logicahome config` to print the resolved path.

## Development

```bash
git clone https://github.com/Rovemark/logicahome.git
cd logicahome
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev,all]"

ruff check src tests
ruff format src tests
pytest -v
```

The project uses [`uv`](https://github.com/astral-sh/uv) for fast environment management, but standard `python -m venv` + `pip install -e ".[dev,all]"` works the same way.

## Roadmap

See [CHANGELOG.md](CHANGELOG.md) for the unreleased work. Open issues for bigger items live in the [GitHub project board](https://github.com/Rovemark/logicahome/issues).

Near-term:

- Real device control in the Tuya adapter (DPS map, brightness/color translation)
- Adapter test harness with mocked vendor APIs
- Native Matter adapter
- Cookbook of example AI prompts and automations

## Contributing

PRs welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [adapter guide](docs/writing-adapters.md). The shortest path to becoming a contributor is shipping a new adapter in a single file.

## Security

If you find a security issue, please **do not open a public issue**. Follow the process in [SECURITY.md](SECURITY.md).

## License

Licensed under the [Apache License 2.0](LICENSE).

Author: [Andre Ambrosio](https://github.com/sirambrosio).
