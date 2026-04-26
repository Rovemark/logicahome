"""CLI — humans and shell scripts."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from logicahome import __version__
from logicahome.adapters import registered_adapters
from logicahome.core.config import config_path, load_config, save_config
from logicahome.runtime import Runtime

app = typer.Typer(
    name="logicahome",
    help="Local-first MCP server and CLI for smart home control.",
    no_args_is_help=True,
    add_completion=False,
)
mcp_app = typer.Typer(help="Run or install the LogicaHome MCP server.", no_args_is_help=True)
device_app = typer.Typer(help="Inspect and control devices.", no_args_is_help=True)
app.add_typer(mcp_app, name="mcp")
app.add_typer(device_app, name="device")

console = Console()


@app.command()
def version() -> None:
    """Print the LogicaHome version."""
    console.print(f"logicahome {__version__}")


@app.command()
def init() -> None:
    """Create the config file and run an initial discovery."""
    cfg_path = config_path()
    if not cfg_path.exists():
        save_config({"adapters": {}})
        console.print(f"[green]Created config at[/] {cfg_path}")
        console.print(
            "Add adapters under `adapters:` then run [cyan]logicahome discover[/] to scan."
        )
        return
    console.print(f"Config already exists at {cfg_path}")


@app.command()
def discover() -> None:
    """Scan all configured adapters and update the registry."""

    async def _run() -> None:
        runtime = Runtime()
        await runtime.initialize()
        if not runtime.adapter_names:
            console.print(
                "[yellow]No adapters configured.[/] Edit "
                f"{config_path()} and add at least one adapter."
            )
            return
        console.print(f"Scanning adapters: {', '.join(runtime.adapter_names)}")
        devices = await runtime.discover_all()
        await runtime.shutdown()
        console.print(f"[green]Found {len(devices)} device(s).[/]")

    asyncio.run(_run())


@app.command()
def adapters() -> None:
    """List all adapters bundled with this LogicaHome install."""
    table = Table(title="Available adapters")
    table.add_column("name", style="cyan")
    table.add_column("import")
    for name in registered_adapters():
        table.add_row(name, f"logicahome.adapters.{name}")
    console.print(table)


@device_app.command("list")
def device_list() -> None:
    """List all devices in the registry."""

    async def _run() -> None:
        runtime = Runtime()
        await runtime.initialize()
        devices = await runtime.list_devices()
        await runtime.shutdown()

        if not devices:
            console.print("[yellow]No devices yet.[/] Run [cyan]logicahome discover[/].")
            return
        table = Table(title=f"{len(devices)} device(s)")
        table.add_column("slug", style="cyan")
        table.add_column("name")
        table.add_column("adapter")
        table.add_column("room")
        table.add_column("capabilities")
        for d in devices:
            table.add_row(
                d.slug,
                d.name,
                d.adapter,
                d.room or "-",
                ", ".join(c.value for c in d.capabilities),
            )
        console.print(table)

    asyncio.run(_run())


@device_app.command("on")
def device_on(slug: str) -> None:
    """Turn a device on."""
    _set_state(slug, on=True)


@device_app.command("off")
def device_off(slug: str) -> None:
    """Turn a device off."""
    _set_state(slug, on=False)


@device_app.command("brightness")
def device_brightness(slug: str, level: int = typer.Argument(..., min=0, max=100)) -> None:
    """Set brightness (0-100)."""
    _set_state(slug, on=level > 0, brightness=level)


@device_app.command("state")
def device_state(slug: str) -> None:
    """Print the current state of a device as JSON."""

    async def _run() -> None:
        runtime = Runtime()
        await runtime.initialize()
        state = await runtime.get_state(slug)
        await runtime.shutdown()
        console.print_json(json.dumps(state.model_dump()))

    asyncio.run(_run())


def _set_state(slug: str, **changes: object) -> None:
    async def _run() -> None:
        runtime = Runtime()
        await runtime.initialize()
        new_state = await runtime.set_state(slug, **changes)
        await runtime.shutdown()
        console.print_json(json.dumps(new_state.model_dump()))

    asyncio.run(_run())


# --- MCP subcommand --------------------------------------------------------


@mcp_app.command("serve")
def mcp_serve() -> None:
    """Run the MCP server over stdio (for Claude Desktop, Antigravity, Cursor, ...)."""
    from logicahome.server import run_stdio_server

    asyncio.run(run_stdio_server())


@mcp_app.command("install")
def mcp_install(
    client: str = typer.Option(
        "claude",
        help="Target client: claude | cursor | print",
    ),
) -> None:
    """Print or install the MCP server config snippet for a given client."""
    snippet = {
        "logicahome": {
            "command": "logicahome",
            "args": ["mcp", "serve"],
        }
    }
    if client == "print":
        console.print_json(json.dumps({"mcpServers": snippet}, indent=2))
        return
    if client == "claude":
        target = _claude_desktop_config_path()
        _merge_into_config_file(target, snippet)
        console.print(f"[green]Updated[/] {target}")
        console.print("Restart Claude Desktop for the change to take effect.")
        return
    if client == "cursor":
        target = Path.home() / ".cursor" / "mcp.json"
        _merge_into_config_file(target, snippet)
        console.print(f"[green]Updated[/] {target}")
        return
    raise typer.BadParameter(f"Unknown client: {client}")


def _claude_desktop_config_path() -> Path:
    import platform

    home = Path.home()
    if platform.system() == "Darwin":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Windows":
        return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    return home / ".config" / "Claude" / "claude_desktop_config.json"


def _merge_into_config_file(path: Path, server_entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    servers = existing.setdefault("mcpServers", {})
    servers.update(server_entry)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


@app.command()
def config() -> None:
    """Print the resolved config and config file path."""
    console.print(f"Config file: {config_path()}")
    console.print_json(json.dumps(load_config(), indent=2))


if __name__ == "__main__":
    app()
