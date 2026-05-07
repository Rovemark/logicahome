"""Starlette app: HTML dashboard + JSON API + (optional) MCP SSE on the same port."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any

from logicahome.core.logging import get_logger
from logicahome.runtime import Runtime

log = get_logger("logicahome.web")
TEMPLATES_DIR = Path(__file__).parent / "templates"


_runtime: Runtime | None = None


async def get_runtime() -> Runtime:
    global _runtime
    if _runtime is None:
        _runtime = Runtime()
        await _runtime.initialize()
    return _runtime


def build_app(*, mount_mcp: bool = True) -> Any:
    """Build the Starlette app.

    `mount_mcp=True` also exposes the MCP server over SSE at /sse — useful
    when you want a single port serving humans, JSON clients, AND remote
    AI clients.
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from starlette.routing import Mount, Route

    from logicahome.web import api as api_module
    from logicahome.web import views as views_module

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=True,
    )
    views_module.set_template_env(env)

    routes: list[Any] = [
        Route("/", views_module.index),
        Route("/devices", views_module.devices_page),
        Route("/scenes", views_module.scenes_page),
        Route("/connect", views_module.connect_page),
        Route("/scan", views_module.scan_page),
        Route("/settings", views_module.settings_page),
        # JSON API
        Route("/api/health", api_module.health),
        Route("/api/devices", api_module.list_devices, methods=["GET"]),
        Route("/api/devices/{slug}", api_module.get_device, methods=["GET"]),
        Route("/api/devices/{slug}/state", api_module.set_device_state, methods=["POST"]),
        Route("/api/scenes", api_module.list_scenes, methods=["GET"]),
        Route("/api/scenes", api_module.save_scene, methods=["POST"]),
        Route("/api/scenes/{slug}/run", api_module.run_scene, methods=["POST"]),
        Route("/api/scenes/{slug}", api_module.delete_scene, methods=["DELETE"]),
        Route("/api/scenes/snapshot", api_module.snapshot_scene, methods=["POST"]),
        Route("/api/discover", api_module.discover, methods=["POST"]),
        Route("/api/scan", api_module.scan, methods=["GET"]),
        Route("/api/adapters", api_module.list_adapters, methods=["GET"]),
        Route("/api/version", api_module.version, methods=["GET"]),
    ]

    if mount_mcp:
        try:
            from mcp.server.sse import SseServerTransport

            from logicahome.server import server as mcp_server

            sse = SseServerTransport("/messages/")

            async def handle_sse(request: Any) -> Any:
                from starlette.responses import Response

                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await mcp_server.run(
                        streams[0],
                        streams[1],
                        mcp_server.create_initialization_options(),
                    )
                return Response()

            routes.append(Route("/sse", endpoint=handle_sse, methods=["GET"]))
            routes.append(Mount("/messages/", app=sse.handle_post_message))
        except Exception as e:
            log.warning("MCP SSE mount skipped: %s", e)

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # local-only by default; tighten in proxy if exposed
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ]

    return Starlette(debug=False, routes=routes, middleware=middleware)


def run_web_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    import uvicorn

    if open_browser:
        import contextlib
        import threading

        def _open_later() -> None:
            import time

            time.sleep(0.6)
            with contextlib.suppress(Exception):
                webbrowser.open(f"http://{host}:{port}/")

        threading.Thread(target=_open_later, daemon=True).start()

    log.info("LogicaHome dashboard on http://%s:%d", host, port)
    uvicorn.run(build_app(), host=host, port=port, log_level="warning")
