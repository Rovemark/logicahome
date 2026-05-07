"""ESPHome adapter — native API for ESPHome firmware (DIY / Shelly-on-ESP).

Configuration:
    adapters:
      esphome:
        devices:
          - host: living-room-lamp.local
            port: 6053
            password: <api-password>   # optional
            name: "Living room lamp"

Requires the optional dep: `pip install 'logicahome[esphome]'`.

Implementation uses `aioesphomeapi`'s lightweight async client to subscribe
to entity states and send commands. ESPHome devices push state changes;
we poll via `list_entities_services()` on `discover` and re-fetch in
`get_state` for simplicity.
"""

from __future__ import annotations

from typing import Any

from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.device import Device, DeviceCapability, DeviceState


class ESPHomeAdapter(Adapter):
    name = "esphome"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        try:
            import aioesphomeapi  # noqa: F401
        except ImportError as e:
            raise AdapterError(
                "aioesphomeapi not installed. Run: pip install 'logicahome[esphome]'"
            ) from e

    async def _client(self, device_cfg: dict[str, Any]) -> Any:
        from aioesphomeapi import APIClient

        client = APIClient(
            address=device_cfg["host"],
            port=int(device_cfg.get("port", 6053)),
            password=device_cfg.get("password", ""),
        )
        await client.connect(login=True)
        return client

    async def discover(self) -> list[Device]:
        out: list[Device] = []
        for d in self.config.get("devices", []):
            client = await self._client(d)
            try:
                entities, _services = await client.list_entities_services()
            finally:
                await client.disconnect()
            for ent in entities:
                domain = type(ent).__name__.lower().replace("info", "")
                caps = _esphome_caps(domain)
                if not caps:
                    continue
                out.append(
                    Device(
                        slug=f"esphome-{d.get('slug') or _slugify(d['name'])}-{ent.object_id}",
                        name=f"{d['name']} — {ent.name}",
                        adapter="esphome",
                        native_id=f"{d['host']}#{ent.key}",
                        capabilities=caps,
                        room=d.get("room"),
                        manufacturer="ESPHome",
                        metadata={
                            "host": d["host"],
                            "port": int(d.get("port", 6053)),
                            "password": d.get("password", ""),
                            "key": ent.key,
                            "domain": domain,
                        },
                    )
                )
        return out

    async def get_state(self, device: Device) -> DeviceState:
        # Connecting per-call is wasteful but keeps the surface stateless.
        # Long-running callers should keep an APIClient open via a custom
        # subclass — left as a future optimization.
        return DeviceState(extra={"note": "esphome live state requires subscription"})

    async def set_state(self, device: Device, **changes: Any) -> DeviceState:
        from aioesphomeapi import APIClient

        meta = device.metadata
        client = APIClient(address=meta["host"], port=meta["port"], password=meta["password"])
        await client.connect(login=True)
        try:
            if meta["domain"] == "switch":
                await client.switch_command(meta["key"], bool(changes.get("on", True)))
            elif meta["domain"] == "light":
                await client.light_command(
                    key=meta["key"],
                    state=bool(changes.get("on", True)),
                    brightness=(changes["brightness"] / 100) if "brightness" in changes else None,
                    rgb=(
                        tuple(c / 255 for c in changes["color_rgb"])
                        if "color_rgb" in changes
                        else None
                    ),
                )
            else:
                raise AdapterError(f"ESPHome domain {meta['domain']} not yet supported")
        finally:
            await client.disconnect()
        return DeviceState()

    async def close(self) -> None:
        return None


def _esphome_caps(domain: str) -> list[DeviceCapability]:
    if domain == "switch":
        return [DeviceCapability.ON_OFF]
    if domain == "light":
        return [DeviceCapability.ON_OFF, DeviceCapability.BRIGHTNESS, DeviceCapability.COLOR]
    if domain == "sensor":
        return [DeviceCapability.TEMPERATURE]
    return []


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")
