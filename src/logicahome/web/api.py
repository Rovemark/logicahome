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


async def get_config(_: Request) -> JSONResponse:
    from logicahome.core.config import load_config

    return JSONResponse(_mask_secrets(load_config()))


async def save_adapter_config(request: Request) -> JSONResponse:
    from logicahome.adapters import registered_adapters
    from logicahome.core.config import load_config, save_config

    name = request.path_params["adapter"]
    if name not in registered_adapters():
        return JSONResponse(
            {"error": {"code": "invalid_input", "message": f"Unknown adapter: {name}"}},
            status_code=400,
        )
    payload = await _json_body(request)
    cfg = load_config()
    cfg.setdefault("adapters", {})[name] = payload
    save_config(cfg)
    from logicahome.web import app as app_module

    app_module._runtime = None  # type: ignore[attr-defined]
    return JSONResponse({"saved": name})


async def delete_adapter_config(request: Request) -> JSONResponse:
    from logicahome.core.config import load_config, save_config

    name = request.path_params["adapter"]
    cfg = load_config()
    cfg.get("adapters", {}).pop(name, None)
    save_config(cfg)
    from logicahome.web import app as app_module

    app_module._runtime = None  # type: ignore[attr-defined]
    return JSONResponse({"removed": name})


async def validate_home_assistant(request: Request) -> JSONResponse:
    from logicahome.wizards import _ha_validate

    payload = await _json_body(request)
    url = (payload.get("url") or "").strip()
    token = payload.get("token") or ""
    if not url or not token:
        return JSONResponse(
            {"error": {"code": "invalid_input", "message": "url and token required"}},
            status_code=400,
        )
    ok, message = await _ha_validate(url, token)
    return JSONResponse({"ok": ok, "message": message})


async def pair_hue(request: Request) -> JSONResponse:
    import aiohttp

    payload = await _json_body(request)
    bridge_ip = (payload.get("bridge_ip") or "").strip()
    if not bridge_ip:
        return JSONResponse(
            {"error": {"code": "invalid_input", "message": "bridge_ip required"}},
            status_code=400,
        )
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
    except Exception as e:
        return JSONResponse(
            {"error": {"code": "adapter_unavailable", "message": str(e)}},
            status_code=400,
        )
    if isinstance(data, list) and data and "success" in data[0]:
        return JSONResponse(
            {"ok": True, "bridge_ip": bridge_ip, "api_key": data[0]["success"]["username"]}
        )
    err = (data[0].get("error", {}) if isinstance(data, list) and data else {}) or {}
    msg = err.get("description", "Did you press the bridge link button in the last 30s?")
    return JSONResponse({"ok": False, "message": msg})


async def detect_home_assistant(_: Request) -> JSONResponse:
    """mDNS scan for Home Assistant on the LAN."""
    try:
        from zeroconf import ServiceBrowser, Zeroconf
    except ImportError:
        return JSONResponse({"hits": []})

    hits: list[dict[str, Any]] = []

    class _Listener:
        def add_service(self, zc: Any, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info and info.addresses:
                ip = ".".join(str(b) for b in info.addresses[0])
                port = info.port or 8123
                hits.append(
                    {
                        "ip": ip,
                        "port": port,
                        "url": f"http://{ip}:{port}",
                        "name": name,
                    }
                )

        def remove_service(self, *_a: Any) -> None:
            pass

        def update_service(self, *_a: Any) -> None:
            pass

    zc = Zeroconf()
    try:
        for service in ("_home-assistant._tcp.local.", "_hass-mobile-app._tcp.local."):
            ServiceBrowser(zc, service, _Listener())
        import time as _time

        _time.sleep(2)
    finally:
        zc.close()
    return JSONResponse({"hits": hits})


async def setup_tuya_cloud(request: Request) -> JSONResponse:
    """Pull every Tuya device + local_key from the Tuya IoT Cloud, save config.

    No terminal wizard required. The user creates a Tuya IoT Cloud project once
    (free tier) and provides the project's Access ID + Access Secret + region.
    The user must also link their SmartLife app to the project (one-time, via
    the Tuya IoT web UI: 'Devices → Link Tuya App Account').
    """
    try:
        import tinytuya  # type: ignore[import-not-found]
    except ImportError:
        return JSONResponse(
            {
                "error": {
                    "code": "adapter_unavailable",
                    "message": "tinytuya not installed",
                    "fix": "Run: pip install 'logicahome[tuya]'",
                }
            },
            status_code=400,
        )

    payload = await _json_body(request)
    api_key = (payload.get("api_key") or "").strip()
    api_secret = (payload.get("api_secret") or "").strip()
    api_region = (payload.get("api_region") or "us").strip().lower()

    if not api_key or not api_secret:
        return JSONResponse(
            {"error": {"code": "invalid_input", "message": "api_key and api_secret required"}},
            status_code=400,
        )

    try:
        cloud = tinytuya.Cloud(
            apiRegion=api_region,
            apiKey=api_key,
            apiSecret=api_secret,
        )
        devices_raw = cloud.getdevices(verbose=True)
    except Exception as e:
        return JSONResponse(
            {"error": {"code": "auth_failed", "message": str(e)}},
            status_code=400,
        )

    if isinstance(devices_raw, dict) and "Error" in devices_raw:
        return JSONResponse(
            {
                "error": {
                    "code": "auth_failed",
                    "message": devices_raw.get("Error"),
                    "fix": "Confirm the Access ID/Secret and that you linked the SmartLife app to the project.",
                }
            },
            status_code=400,
        )

    if not isinstance(devices_raw, list):
        return JSONResponse(
            {"error": {"code": "internal_error", "message": "Unexpected Tuya cloud response"}},
            status_code=500,
        )

    parsed: list[dict[str, Any]] = []
    for d in devices_raw:
        if not d.get("id") or not d.get("key"):
            continue
        parsed.append(
            {
                "id": d.get("id"),
                "ip": d.get("ip", ""),
                "local_key": d.get("key"),
                "name": d.get("name", d.get("id")),
                "version": str(d.get("version", "3.4")),
                "manufacturer": "Tuya",
                "model": d.get("category"),
                "capabilities": _tuya_caps_from_category(d.get("category", "")),
            }
        )

    from logicahome.core.config import load_config, save_config

    cfg = load_config()
    cfg.setdefault("adapters", {})["tuya"] = {"devices": parsed}
    save_config(cfg)
    from logicahome.web import app as app_module

    app_module._runtime = None  # type: ignore[attr-defined]

    return JSONResponse({"ok": True, "device_count": len(parsed), "devices": parsed})


def _tuya_caps_from_category(category: str) -> list[str]:
    cat = (category or "").lower()
    if any(k in cat for k in ["dj", "light", "lamp"]):
        return ["on_off", "brightness", "color"]
    if "cz" in cat:
        return ["on_off", "power_metering"]
    return ["on_off"]


async def discover_one(request: Request) -> JSONResponse:
    from logicahome.adapters import load_adapter
    from logicahome.core.config import load_config

    name = request.path_params["adapter"]
    cfg = load_config().get("adapters", {}).get(name)
    if cfg is None:
        return JSONResponse(
            {"error": {"code": "adapter_not_configured", "message": name}},
            status_code=400,
        )
    try:
        adapter = load_adapter(name, cfg)
        devices = await adapter.discover()
        await adapter.close()
        rt = await get_runtime()
        for d in devices:
            await rt.registry.upsert(d)
    except Exception as e:
        return _err(e, adapter=name)
    return JSONResponse(
        {"adapter": name, "discovered": len(devices), "devices": [d.model_dump() for d in devices]}
    )


SECRET_KEYS = {"token", "api_key", "local_key", "password"}


def _mask_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("***" if k in SECRET_KEYS and v else _mask_secrets(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mask_secrets(x) for x in obj]
    return obj


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        raw = await request.body()
        return json.loads(raw or b"{}")
    except json.JSONDecodeError:
        return {}
