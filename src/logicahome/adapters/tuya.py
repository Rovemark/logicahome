"""Tuya / SmartLife adapter — local LAN protocol, no cloud required.

Configuration (in config.yaml):
    adapters:
      tuya:
        devices:
          - id: bf12345...        # device_id from Tuya
            ip: 192.168.0.42
            local_key: <key>
            version: 3.4
            name: "Sala — luminária"
            capabilities: [on_off, brightness]

The local_key is obtained once via tinytuya wizard or the Tuya IoT cloud
console. After that, no internet is required.
"""

from __future__ import annotations

from typing import Any

from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.device import Device, DeviceCapability, DeviceState


class TuyaAdapter(Adapter):
    name = "tuya"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        try:
            import tinytuya  # noqa: F401
        except ImportError as e:
            raise AdapterError("tinytuya not installed. Run: pip install 'logicahome[tuya]'") from e

    async def discover(self) -> list[Device]:
        devices_cfg = self.config.get("devices", [])
        result: list[Device] = []
        for d in devices_cfg:
            caps = [DeviceCapability(c) for c in d.get("capabilities", ["on_off"])]
            result.append(
                Device(
                    slug=d.get("slug") or _slugify(d["name"]),
                    name=d["name"],
                    adapter="tuya",
                    native_id=d["id"],
                    capabilities=caps,
                    room=d.get("room"),
                    manufacturer=d.get("manufacturer", "Tuya"),
                    model=d.get("model"),
                    metadata={
                        "ip": d["ip"],
                        "version": d.get("version", "3.4"),
                    },
                )
            )
        return result

    async def get_state(self, device: Device) -> DeviceState:
        # TODO(adapter): wire tinytuya.OutletDevice and parse DPS map
        return DeviceState()

    async def set_state(self, device: Device, **changes: Any) -> DeviceState:
        # TODO(adapter): translate (on, brightness, color) -> Tuya DPS calls
        return DeviceState(**{k: v for k, v in changes.items() if k in DeviceState.model_fields})

    async def close(self) -> None:
        return None


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("—", "-").replace("/", "-")
