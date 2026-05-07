"""Web dashboard — local-first UI and JSON API.

Same Runtime as the CLI and MCP server. The HTML side uses htmx + Pico CSS
(zero build, zero npm). The JSON side is the integration point for any
external dashboard (LogicaOS, n8n, custom scripts).
"""

from logicahome.web.app import build_app, run_web_server

__all__ = ["build_app", "run_web_server"]
