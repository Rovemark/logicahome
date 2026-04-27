"""Runtime — orchestrates registry + adapters.

Both the CLI and the MCP server consume this module. Anything stateful that
isn't tied to a specific surface (CLI vs MCP) lives here.
"""

from __future__ import annotations

import asyncio
from typing import Any

from logicahome.adapters import load_adapter
from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.config import load_config
from logicahome.core.device import Device, DeviceState
from logicahome.core.registry import Registry
from logicahome.core.scene import Scene, SceneAction


class Runtime:
    def __init__(self) -> None:
        self.registry = Registry()
        self._config = load_config()
        self._adapters: dict[str, Adapter] = {}

    async def initialize(self) -> None:
        await self.registry.initialize()
        for name, cfg in self._config.get("adapters", {}).items():
            try:
                self._adapters[name] = load_adapter(name, cfg or {})
            except AdapterError:
                # Adapter failed to construct (e.g. missing optional dep).
                # Skip — discover/state calls for it will surface the error.
                continue

    async def shutdown(self) -> None:
        for adapter in self._adapters.values():
            await adapter.close()

    @property
    def adapter_names(self) -> list[str]:
        return list(self._adapters.keys())

    async def discover_all(self) -> list[Device]:
        found: list[Device] = []
        for adapter in self._adapters.values():
            try:
                devices = await adapter.discover()
            except Exception as e:
                raise AdapterError(f"discover failed for {adapter.name}: {e}") from e
            for d in devices:
                await self.registry.upsert(d)
                found.append(d)
        return found

    async def list_devices(self) -> list[Device]:
        return await self.registry.list_all()

    async def get_state(self, slug: str) -> DeviceState:
        device = await self._require_device(slug)
        return await self._adapter_for(device).get_state(device)

    async def set_state(self, slug: str, **changes: Any) -> DeviceState:
        device = await self._require_device(slug)
        return await self._adapter_for(device).set_state(device, **changes)

    # --- scenes ------------------------------------------------------------

    async def list_scenes(self) -> list[Scene]:
        return await self.registry.list_scenes()

    async def save_scene(self, scene: Scene) -> None:
        await self.registry.upsert_scene(scene)

    async def remove_scene(self, slug: str) -> bool:
        return await self.registry.remove_scene(slug)

    async def run_scene(self, slug: str) -> dict[str, Any]:
        """Apply every action in a scene concurrently.

        Returns a per-device status map: {slug: {"ok": bool, "error": str?}}.
        Failures on one device do not abort the others.
        """
        scene = await self.registry.get_scene(slug)
        if scene is None:
            raise AdapterError(f"Unknown scene: {slug}")

        async def _apply(action: SceneAction) -> tuple[str, dict[str, Any]]:
            try:
                await self.set_state(action.device_slug, **action.to_changes())
                return action.device_slug, {"ok": True}
            except Exception as e:
                return action.device_slug, {"ok": False, "error": str(e)}

        results = await asyncio.gather(*[_apply(a) for a in scene.actions])
        return {"scene": slug, "results": dict(results)}

    async def snapshot_scene(self, slug: str, name: str, description: str | None = None) -> Scene:
        """Capture the current state of every known device as a new scene."""
        devices = await self.registry.list_all()
        actions: list[SceneAction] = []
        for d in devices:
            try:
                state = await self.get_state(d.slug)
            except Exception:
                continue
            actions.append(
                SceneAction(
                    device_slug=d.slug,
                    on=state.on,
                    brightness=state.brightness,
                    color_rgb=state.color_rgb,
                    color_temp_kelvin=state.color_temp_kelvin,
                )
            )
        scene = Scene(slug=slug, name=name, description=description, actions=actions)
        await self.save_scene(scene)
        return scene

    async def _require_device(self, slug: str) -> Device:
        device = await self.registry.get(slug)
        if device is None:
            raise AdapterError(f"Unknown device: {slug}")
        return device

    def _adapter_for(self, device: Device) -> Adapter:
        adapter = self._adapters.get(device.adapter)
        if adapter is None:
            raise AdapterError(
                f"Adapter '{device.adapter}' is not configured. "
                f"Add it under `adapters:` in config.yaml."
            )
        return adapter
