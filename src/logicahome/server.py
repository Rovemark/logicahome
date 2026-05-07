"""MCP server — exposes the runtime as MCP tools over stdio.

Any client that speaks Model Context Protocol (Claude Desktop, Antigravity,
Cursor, ChatGPT with MCP, ...) can connect to this and control the home.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from logicahome.core.errors import StructuredError
from logicahome.core.logging import get_logger
from logicahome.runtime import Runtime

log = get_logger("logicahome.server")
server: Server = Server("logicahome")
_runtime: Runtime | None = None


async def _ensure_runtime() -> Runtime:
    global _runtime
    if _runtime is None:
        _runtime = Runtime()
        await _runtime.initialize()
    return _runtime


def _structured_error_text(exc: BaseException, **context: Any) -> str:
    err = StructuredError.from_exception(exc, **context)
    return json.dumps({"error": err.model_dump(exclude_none=True)}, indent=2)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_devices",
            description=(
                "List every device known to LogicaHome. Use this first to discover "
                "what slugs exist before calling other tools."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_state",
            description="Get the current state of a device by slug.",
            inputSchema={
                "type": "object",
                "properties": {"slug": {"type": "string"}},
                "required": ["slug"],
            },
        ),
        Tool(
            name="turn_on",
            description="Turn a device on. Optionally set brightness (0-100).",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "brightness": {"type": "integer", "minimum": 0, "maximum": 100},
                },
                "required": ["slug"],
            },
        ),
        Tool(
            name="turn_off",
            description="Turn a device off.",
            inputSchema={
                "type": "object",
                "properties": {"slug": {"type": "string"}},
                "required": ["slug"],
            },
        ),
        Tool(
            name="set_brightness",
            description="Set the brightness of a device (0-100). Implies on.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "brightness": {"type": "integer", "minimum": 0, "maximum": 100},
                },
                "required": ["slug", "brightness"],
            },
        ),
        Tool(
            name="set_color",
            description="Set RGB color of a device (each channel 0-255).",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "r": {"type": "integer", "minimum": 0, "maximum": 255},
                    "g": {"type": "integer", "minimum": 0, "maximum": 255},
                    "b": {"type": "integer", "minimum": 0, "maximum": 255},
                },
                "required": ["slug", "r", "g", "b"],
            },
        ),
        Tool(
            name="discover",
            description=(
                "Re-scan all configured adapters and update the device registry. "
                "Use this after the user adds new devices to their network."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_scenes",
            description=(
                "List every saved scene (multi-device state snapshot). "
                "Use this to discover scene slugs before calling run_scene."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="run_scene",
            description=(
                "Apply a saved scene by slug. Each device action runs concurrently; "
                "failures on one device do not abort the others. Returns a per-device "
                "status map."
            ),
            inputSchema={
                "type": "object",
                "properties": {"slug": {"type": "string"}},
                "required": ["slug"],
            },
        ),
        Tool(
            name="snapshot_scene",
            description=(
                "Capture the current state of every known device as a new scene. "
                "Useful when the user says 'save this as bedtime' — read every device, "
                "store the snapshot, then run_scene('bedtime') reproduces it later."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["slug", "name"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    log.debug("tool call: %s args=%s", name, arguments)
    try:
        return await _dispatch(name, arguments)
    except Exception as exc:
        log.warning("tool %s failed: %s", name, exc)
        ctx: dict[str, Any] = {}
        if "slug" in arguments:
            ctx["device_slug"] = arguments["slug"]
        return [TextContent(type="text", text=_structured_error_text(exc, **ctx))]


async def _dispatch(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    rt = await _ensure_runtime()

    if name == "list_devices":
        devices = await rt.list_devices()
        payload = [d.model_dump() for d in devices]
        return [TextContent(type="text", text=json.dumps(payload, indent=2))]

    if name == "get_state":
        state = await rt.get_state(arguments["slug"])
        return [TextContent(type="text", text=json.dumps(state.model_dump(), indent=2))]

    if name == "turn_on":
        changes: dict[str, Any] = {"on": True}
        if "brightness" in arguments:
            changes["brightness"] = arguments["brightness"]
        state = await rt.set_state(arguments["slug"], **changes)
        return [TextContent(type="text", text=json.dumps(state.model_dump(), indent=2))]

    if name == "turn_off":
        state = await rt.set_state(arguments["slug"], on=False)
        return [TextContent(type="text", text=json.dumps(state.model_dump(), indent=2))]

    if name == "set_brightness":
        state = await rt.set_state(
            arguments["slug"], on=arguments["brightness"] > 0, brightness=arguments["brightness"]
        )
        return [TextContent(type="text", text=json.dumps(state.model_dump(), indent=2))]

    if name == "set_color":
        state = await rt.set_state(
            arguments["slug"],
            on=True,
            color_rgb=(arguments["r"], arguments["g"], arguments["b"]),
        )
        return [TextContent(type="text", text=json.dumps(state.model_dump(), indent=2))]

    if name == "discover":
        devices = await rt.discover_all()
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"discovered": len(devices), "devices": [d.model_dump() for d in devices]},
                    indent=2,
                ),
            )
        ]

    if name == "list_scenes":
        scenes = await rt.list_scenes()
        return [
            TextContent(type="text", text=json.dumps([s.model_dump() for s in scenes], indent=2))
        ]

    if name == "run_scene":
        result = await rt.run_scene(arguments["slug"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    if name == "snapshot_scene":
        scene = await rt.snapshot_scene(
            slug=arguments["slug"],
            name=arguments["name"],
            description=arguments.get("description"),
        )
        return [TextContent(type="text", text=json.dumps(scene.model_dump(), indent=2))]

    raise ValueError(f"Unknown tool: {name}")


async def run_stdio_server() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())
