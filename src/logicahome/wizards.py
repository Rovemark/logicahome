"""Interactive wizards — guided onboarding for each adapter.

Wizards are the answer to "how does someone actually plug in their devices?"
Each adapter that requires non-trivial setup ships a wizard. The wizard:

  1. Explains what's needed and where to get it.
  2. Prompts for the minimum required values.
  3. Validates against the real service before saving.
  4. Writes the result into the user config under `adapters.<name>`.

Wizards never persist secrets anywhere except `config.yaml`.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import aiohttp
import typer
from rich.console import Console
from rich.panel import Panel

from logicahome.core.config import load_config, save_config

console = Console()


# --- Home Assistant -------------------------------------------------------


async def _ha_validate(url: str, token: str) -> tuple[bool, str]:
    """Hit `/api/` to confirm URL + token are valid."""
    try:
        async with (
            aiohttp.ClientSession(headers={"Authorization": f"Bearer {token}"}) as session,
            session.get(
                f"{url.rstrip('/')}/api/",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp,
        ):
            if resp.status == 200:
                data = await resp.json()
                return True, data.get("message", "OK")
            return False, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)


def connect_home_assistant() -> None:
    console.print(
        Panel(
            "[bold]Home Assistant[/]\n\n"
            "You need:\n"
            "  • The URL of your HA install (e.g. http://homeassistant.local:8123)\n"
            "  • A long-lived access token\n\n"
            "How to get a token:\n"
            "  1. Open your HA web UI.\n"
            "  2. Click your profile (bottom-left).\n"
            "  3. Scroll to [italic]Long-Lived Access Tokens[/] and click [italic]Create Token[/].\n"
            "  4. Copy the token (you only see it once).",
            title="Connect — home_assistant",
            border_style="cyan",
        )
    )

    url = typer.prompt("HA URL", default="http://homeassistant.local:8123")
    token = typer.prompt("Access token", hide_input=True)
    domains_raw = typer.prompt(
        "Domains to expose (comma-separated)",
        default="light,switch,climate,lock,scene",
    )
    domains = [d.strip() for d in domains_raw.split(",") if d.strip()]

    console.print("\n[dim]Validating...[/]")
    ok, message = asyncio.run(_ha_validate(url, token))
    if not ok:
        console.print(f"[red]Validation failed:[/] {message}")
        if not typer.confirm("Save anyway?", default=False):
            raise typer.Exit(1)
    else:
        console.print(f"[green]✓[/] HA responded: {message}")

    cfg = load_config()
    cfg.setdefault("adapters", {})["home_assistant"] = {
        "url": url,
        "token": token,
        "include_domains": domains,
    }
    save_config(cfg)
    console.print("\n[green]Saved.[/] Run [cyan]logicahome discover[/] to import devices.")


# --- Tuya / SmartLife -----------------------------------------------------


def connect_tuya() -> None:
    console.print(
        Panel(
            "[bold]Tuya / SmartLife[/]\n\n"
            "Tuya speaks a local LAN protocol that requires a per-device "
            "[italic]local_key[/]. The easiest way to obtain those keys is the "
            "official [italic]tinytuya wizard[/], which logs into the Tuya IoT "
            "Cloud once and downloads metadata for all your devices.\n\n"
            "You need a Tuya IoT account and a Cloud project linked to your "
            "SmartLife app. Setup guide:\n"
            "  https://github.com/jasonacox/tinytuya#setup-wizard\n\n"
            "After this wizard runs, your devices and keys are saved locally "
            "(no cloud calls during normal operation).",
            title="Connect — tuya",
            border_style="cyan",
        )
    )

    if not _has_tinytuya():
        console.print(
            "[yellow]tinytuya is not installed.[/] Run:\n"
            "  pip install 'logicahome[tuya]'\n"
            "then rerun [cyan]logicahome connect tuya[/]."
        )
        raise typer.Exit(1)

    if not typer.confirm("Run the tinytuya wizard now?", default=True):
        raise typer.Abort()

    work_dir = Path.cwd()
    console.print(f"\n[dim]The wizard will create devices.json + snapshot.json in {work_dir}.[/]\n")
    try:
        subprocess.run(["python", "-m", "tinytuya", "wizard"], check=True)
    except subprocess.CalledProcessError:
        console.print("[red]tinytuya wizard exited with an error.[/]")
        raise typer.Exit(1) from None

    devices_file = work_dir / "devices.json"
    if not devices_file.exists():
        console.print(f"[red]Could not find devices.json at {devices_file}.[/] Re-run the wizard.")
        raise typer.Exit(1)

    devices = _import_tinytuya_devices(devices_file)
    if not devices:
        console.print("[yellow]No devices were imported.[/]")
        return

    cfg = load_config()
    cfg.setdefault("adapters", {})["tuya"] = {"devices": devices}
    save_config(cfg)
    console.print(
        f"\n[green]Saved {len(devices)} device(s).[/] "
        "Run [cyan]logicahome discover[/] to register them."
    )


def _has_tinytuya() -> bool:
    try:
        import tinytuya  # noqa: F401

        return True
    except ImportError:
        return False


def _import_tinytuya_devices(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for d in raw:
        out.append(
            {
                "id": d.get("id"),
                "ip": d.get("ip", ""),
                "local_key": d.get("key"),
                "version": str(d.get("version", "3.4")),
                "name": d.get("name", d.get("id", "tuya-device")),
                "capabilities": _guess_capabilities(d),
            }
        )
    return out


def _guess_capabilities(d: dict[str, Any]) -> list[str]:
    """Best-effort capability guess from tinytuya category metadata."""
    category = (d.get("category") or "").lower()
    if any(k in category for k in ["dj", "light", "lamp"]):
        return ["on_off", "brightness", "color"]
    if "cz" in category:
        return ["on_off", "power_metering"]
    if "sw" in category:
        return ["on_off"]
    return ["on_off"]


# --- Philips Hue ----------------------------------------------------------


def connect_hue() -> None:
    console.print(
        Panel(
            "[bold]Philips Hue[/]\n\n"
            "You need:\n"
            "  • The IP of your Hue Bridge on the LAN\n"
            "    (visit https://discovery.meethue.com to discover it)\n"
            "  • Physical access to the Bridge — you'll press its link button\n\n"
            "This wizard will press through the official user-creation flow:\n"
            "  1. Press the Bridge's round link button now.\n"
            "  2. Within 30 seconds, this wizard POSTs to /api to create a key.\n"
            "  3. Bridge returns the key, we save it. Done.",
            title="Connect — hue",
            border_style="cyan",
        )
    )

    bridge_ip = typer.prompt("Hue Bridge IP")
    typer.confirm("Did you press the Bridge's link button just now?", default=True, abort=True)

    async def _create_key() -> tuple[bool, str]:
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"http://{bridge_ip}/api",
                    json={"devicetype": "logicahome#user"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp,
            ):
                data = await resp.json()
            if isinstance(data, list) and data and "success" in data[0]:
                return True, data[0]["success"]["username"]
            err = data[0].get("error", {}) if isinstance(data, list) and data else {}
            return False, err.get("description", str(data))
        except Exception as e:
            return False, str(e)

    ok, result = asyncio.run(_create_key())
    if not ok:
        console.print(f"[red]Failed:[/] {result}")
        raise typer.Exit(1)

    cfg = load_config()
    cfg.setdefault("adapters", {})["hue"] = {"bridge_ip": bridge_ip, "api_key": result}
    save_config(cfg)
    console.print("\n[green]Saved.[/] Run [cyan]logicahome discover[/] to import lights.")


# --- Shelly ---------------------------------------------------------------


def connect_shelly() -> None:
    console.print(
        Panel(
            "[bold]Shelly[/]\n\n"
            "Shelly devices are configured manually for now — there's no LAN-wide\n"
            "wizard that authenticates against unknown devices safely.\n\n"
            "Open your config file and add entries under `adapters.shelly.devices`:\n"
            "  - ip: 192.168.0.30\n"
            '    name: "Hall plug"\n'
            "    gen: 2          # 1 or 2\n"
            "    channel: 0\n\n"
            "Run [cyan]logicahome scan[/] to find candidate IPs on your LAN.",
            title="Connect — shelly",
            border_style="cyan",
        )
    )


# --- Network scan ---------------------------------------------------------


def scan_network() -> list[dict[str, Any]]:
    """Passive scan for devices on the local network. Returns a list of hits."""
    hits: list[dict[str, Any]] = []
    if _has_tinytuya():
        try:
            import tinytuya

            console.print("[dim]Scanning for Tuya devices on LAN (UDP broadcast)...[/]")
            devices = tinytuya.deviceScan(False, 6)  # 6s scan, no verbose
            for ip, info in devices.items():
                hits.append(
                    {
                        "adapter": "tuya",
                        "ip": ip,
                        "id": info.get("gwId"),
                        "version": info.get("version"),
                    }
                )
        except Exception as e:
            console.print(f"[yellow]Tuya scan failed:[/] {e}")
    hits.extend(_scan_mdns())
    return hits


def _scan_mdns() -> list[dict[str, Any]]:
    """mDNS / zeroconf scan for Hue, HomeKit, ESPHome, Matter, etc."""
    try:
        from zeroconf import ServiceBrowser, Zeroconf
    except ImportError:
        return []

    services = [
        ("_hue._tcp.local.", "hue"),
        ("_hap._tcp.local.", "homekit"),
        ("_esphomelib._tcp.local.", "esphome"),
        ("_matter._tcp.local.", "matter"),
        ("_shelly._tcp.local.", "shelly"),
    ]
    hits: list[dict[str, Any]] = []

    class _Listener:
        def __init__(self, label: str) -> None:
            self.label = label

        def remove_service(self, *_a: Any) -> None:
            pass

        def update_service(self, *_a: Any) -> None:
            pass

        def add_service(self, zc: Any, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info and info.addresses:
                ip = ".".join(str(b) for b in info.addresses[0])
                hits.append({"adapter": self.label, "ip": ip, "id": name, "version": "mdns"})

    zc = Zeroconf()
    browsers: list[ServiceBrowser] = []
    try:
        console.print("[dim]Scanning mDNS for Hue/HomeKit/ESPHome/Matter/Shelly (3s)...[/]")
        for service, label in services:
            browsers.append(ServiceBrowser(zc, service, _Listener(label)))
        import time as _time

        _time.sleep(3)
    except Exception as e:
        console.print(f"[yellow]mDNS scan failed:[/] {e}")
    finally:
        zc.close()
    return hits
