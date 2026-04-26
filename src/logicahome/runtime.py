"""Runtime — orchestrates registry + adapters.

Both the CLI and the MCP server consume this module. Anything stateful that
isn't tied to a specific surface (CLI vs MCP) lives here.
"""

from __future__ import annotations

from typing import Any

from logicahome.adapters import load_adapter
from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.config import load_config
from logicahome.core.device import Device, DeviceState
from logicahome.core.registry import Registry


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
