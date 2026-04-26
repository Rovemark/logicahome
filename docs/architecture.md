# Architecture

LogicaHome is built around one principle: **the same core powers two surfaces** — the CLI (humans, scripts) and the MCP server (any AI client). Adding a third surface (REST, WebSocket, gRPC) means writing one more thin wrapper, never touching the core.

## Layers

```
+-------------------------------------------------------+
|  Surfaces                                             |
|  +-------------------+   +-------------------------+  |
|  |  logicahome.cli   |   |   logicahome.server     |  |
|  |  (Typer + Rich)   |   |   (MCP over stdio/SSE)  |  |
|  +---------+---------+   +-----------+-------------+  |
|            |                         |                |
|            +-----------+-------------+                |
|                        |                              |
|  Runtime               v                              |
|  +-----------------------------------------------+    |
|  |  logicahome.runtime.Runtime                   |    |
|  |  (registry + adapter dispatch + lifecycle)    |    |
|  +-----------------------------------------------+    |
|                        |                              |
|  Core                  v                              |
|  +---------------------+ +-------------------------+  |
|  |  Registry (SQLite)  | |  Adapter (abstract)     |  |
|  +---------------------+ +-----------+-------------+  |
|                                      |                |
|  Adapters                            v                |
|  +-----------+ +----------------+ +----------+        |
|  |  Tuya     | | Home Assistant | | Matter   | ...    |
|  +-----------+ +----------------+ +----------+        |
+-------------------------------------------------------+
                        |
                        v
                 Devices on the LAN
```

## Identity model

Every device has two identifiers:

- `native_id` — the id the adapter's vendor uses (e.g. Tuya `device_id`, HA `light.living_room`). Adapters round-trip this.
- `slug` — a stable, user-facing string (`living-room-lamp`). Slugs are what the AI and the CLI use.

The `(adapter, native_id)` pair is unique. The `slug` is unique on its own.

## State

Two persistence boundaries:

1. **Registry (SQLite)** — what devices exist, their metadata, capabilities. Survives restarts.
2. **Live state** — fetched on demand from the adapter via `get_state`. Never cached aggressively; smart-home state is allowed to drift.

This is deliberate. A cached "the light is on" that's wrong is worse than no cache.

## Tool surface (MCP)

The MCP server exposes seven tools today: `list_devices`, `get_state`, `turn_on`, `turn_off`, `set_brightness`, `set_color`, `discover`. The full schema is in [`src/logicahome/server.py`](../src/logicahome/server.py).

New capabilities (lock/unlock, set temperature, run scene) get new tools as adapters need them. Tools are flat by design — no nested intent parsing — because the AI client is the intent parser.

## Why not REST?

REST works but doesn't carry tool schemas or persistent connections. MCP gives both for free. A REST surface is welcome as a future contribution if there is demand from non-AI integrators.
