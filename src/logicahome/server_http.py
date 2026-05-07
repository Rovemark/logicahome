"""MCP server over HTTP/SSE — for remote clients (Claude.ai web, ChatGPT cloud).

Wraps the same `Server` instance from `logicahome.server` in an SSE
transport mounted via Starlette/Uvicorn. Use this when the AI client lives
outside your machine.

Run:
    logicahome mcp serve --http --host 0.0.0.0 --port 8765

Security note: HTTP/SSE has no built-in auth. If you expose this beyond
localhost, put it behind a reverse proxy with a token check. The default
host is `127.0.0.1` for that reason.
"""

from __future__ import annotations

from typing import Any

from logicahome.core.logging import get_logger

log = get_logger("logicahome.server_http")


def build_app() -> Any:
    """Build a Starlette app exposing the MCP server over SSE."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Mount, Route

    from logicahome.server import server

    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> Response:
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())
        return Response()

    return Starlette(
        debug=False,
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def run_http_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    log.info("Starting LogicaHome MCP HTTP/SSE server on %s:%d", host, port)
    uvicorn.run(build_app(), host=host, port=port, log_level="warning")
