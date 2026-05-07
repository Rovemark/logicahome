"""HTML views — htmx + Pico CSS templates rendered by Jinja2."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

from logicahome import __version__
from logicahome.adapters import registered_adapters
from logicahome.web.app import get_runtime

_env: Any = None


def set_template_env(env: Any) -> None:
    global _env
    _env = env


async def _render(name: str, **ctx: Any) -> HTMLResponse:
    template = _env.get_template(name)
    html = await template.render_async(version=__version__, **ctx)
    return HTMLResponse(html)


async def index(_: Request) -> HTMLResponse:
    rt = await get_runtime()
    devices = await rt.list_devices()
    scenes = await rt.list_scenes()
    return await _render(
        "index.html",
        devices=devices,
        scenes=scenes,
        adapters_configured=rt.adapter_names,
    )


async def devices_page(_: Request) -> HTMLResponse:
    rt = await get_runtime()
    devices = await rt.list_devices()
    return await _render("devices.html", devices=devices)


async def scenes_page(_: Request) -> HTMLResponse:
    rt = await get_runtime()
    scenes = await rt.list_scenes()
    devices = await rt.list_devices()
    return await _render("scenes.html", scenes=scenes, devices=devices)


async def connect_page(_: Request) -> HTMLResponse:
    return await _render("connect.html", adapters=registered_adapters())


async def scan_page(_: Request) -> HTMLResponse:
    return await _render("scan.html")


async def settings_page(_: Request) -> HTMLResponse:
    rt = await get_runtime()
    return await _render(
        "settings.html",
        adapters_configured=rt.adapter_names,
        adapters_available=registered_adapters(),
    )
