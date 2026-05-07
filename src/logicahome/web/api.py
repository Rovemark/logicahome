"""JSON API — what every external dashboard talks to.

The LogicaOS dashboard (private, in the brain) consumes these exact
endpoints. So does any third-party tool.
"""

from __future__ import annotations

import json
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from logicahome import __version__
from logicahome.adapters import registered_adapters
from logicahome.core.errors import StructuredError
from logicahome.core.scene import Scene, SceneAction
from logicahome.web.app import get_runtime


def _err(exc: BaseException, **ctx: Any) -> JSONResponse:
    err = StructuredError.from_exception(exc, **ctx)
    return JSONResponse({"error": err.model_dump(exclude_none=True)}, status_code=400)


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "version": __version__})


async def version(_: Request) -> JSONResponse:
    return JSONResponse({"version": __version__})


async def list_adapters(_: Request) -> JSONResponse:
    return JSONResponse({"adapters": registered_adapters()})


async def list_devices(_: Request) -> JSONResponse:
    rt = await get_runtime()
    devices = await rt.list_devices()
    return JSONResponse({"devices": [d.model_dump() for d in devices]})


async def get_device(request: Request) -> JSONResponse:
    slug = request.path_params["slug"]
    rt = await get_runtime()
    try:
        state = await rt.get_state(slug)
    except Exception as e:
        return _err(e, device_slug=slug)
    return JSONResponse({"slug": slug, "state": state.model_dump(exclude_none=True)})


async def set_device_state(request: Request) -> JSONResponse:
    slug = request.path_params["slug"]
    payload = await _json_body(request)
    rt = await get_runtime()
    try:
        new_state = await rt.set_state(slug, **payload)
    except Exception as e:
        return _err(e, device_slug=slug)
    return JSONResponse({"slug": slug, "state": new_state.model_dump(exclude_none=True)})


async def list_scenes(_: Request) -> JSONResponse:
    rt = await get_runtime()
    scenes = await rt.list_scenes()
    return JSONResponse({"scenes": [s.model_dump() for s in scenes]})


async def save_scene(request: Request) -> JSONResponse:
    payload = await _json_body(request)
    try:
        scene = Scene(
            slug=payload["slug"],
            name=payload["name"],
            description=payload.get("description"),
            actions=[SceneAction(**a) for a in payload.get("actions", [])],
        )
    except Exception as e:
        return _err(e)
    rt = await get_runtime()
    await rt.save_scene(scene)
    return JSONResponse({"saved": scene.slug})


async def run_scene(request: Request) -> JSONResponse:
    slug = request.path_params["slug"]
    rt = await get_runtime()
    try:
        result = await rt.run_scene(slug)
    except Exception as e:
        return _err(e, scene_slug=slug)
    return JSONResponse(result)


async def delete_scene(request: Request) -> JSONResponse:
    slug = request.path_params["slug"]
    rt = await get_runtime()
    removed = await rt.remove_scene(slug)
    return JSONResponse({"removed": removed, "slug": slug})


async def snapshot_scene(request: Request) -> JSONResponse:
    payload = await _json_body(request)
    rt = await get_runtime()
    try:
        scene = await rt.snapshot_scene(
            slug=payload["slug"],
            name=payload["name"],
            description=payload.get("description"),
        )
    except Exception as e:
        return _err(e)
    return JSONResponse(scene.model_dump())


async def discover(_: Request) -> JSONResponse:
    rt = await get_runtime()
    try:
        devices = await rt.discover_all()
    except Exception as e:
        return _err(e)
    return JSONResponse({"discovered": len(devices), "devices": [d.model_dump() for d in devices]})


async def scan(_: Request) -> JSONResponse:
    from logicahome.wizards import scan_network

    return JSONResponse({"hits": scan_network()})


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        raw = await request.body()
        return json.loads(raw or b"{}")
    except json.JSONDecodeError:
        return {}
