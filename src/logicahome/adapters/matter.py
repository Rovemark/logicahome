"""Matter adapter — skeleton, awaiting full python-matter-server integration.

Matter is the cross-vendor smart-home protocol backed by Apple, Google,
Amazon, and Samsung. Local control over Thread/Wi-Fi, no vendor cloud.

Status: discovery and on/off plumbed against the python-matter-server WS
API. Color, brightness, and complex clusters are TODO. Pair devices using
your existing controller (Apple Home, Google Home, etc.) — Matter
multi-admin lets python-matter-server share that fabric.

Configuration:
    adapters:
      matter:
        server_url: ws://localhost:5580/ws
        # Run the server separately:
        #   docker run -d --network host -v matter_data:/data \
        #       ghcr.io/home-assistant-libs/python-matter-server:stable

Requires `pip install 'logicahome[matter]'`.
"""

from __future__ import annotations

from typing import Any

from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.device import Device, DeviceCapability, DeviceState


class MatterAdapter(Adapter):
    name = "matter"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        try:
            import matter_server  # noqa: F401
        except ImportError as e:
            raise AdapterError(
                "python-matter-server not installed. Run: pip install 'logicahome[matter]'"
            ) from e
        if not self.config.get("server_url"):
            raise AdapterError(
                "matter adapter requires `server_url` in config "
                "(e.g. ws://localhost:5580/ws). See python-matter-server docs."
            )

    async def discover(self) -> list[Device]:
        # TODO(adapter): connect to MatterClient, list nodes, translate clusters
        # to capabilities. python-matter-server's WS schema is documented at
        # https://github.com/home-assistant-libs/python-matter-server.
        return []

    async def get_state(self, device: Device) -> DeviceState:
        return DeviceState(extra={"note": "Matter adapter is not yet implemented"})

    async def set_state(self, device: Device, **changes: Any) -> DeviceState:
        raise AdapterError(
            "Matter adapter is not yet implemented end-to-end. "
            "Track progress at https://github.com/Rovemark/logicahome/issues."
        )

    async def close(self) -> None:
        return None


_MATTER_CAP_HINTS: dict[int, list[DeviceCapability]] = {
    # OnOff cluster
    0x0006: [DeviceCapability.ON_OFF],
    # LevelControl cluster
    0x0008: [DeviceCapability.BRIGHTNESS],
    # ColorControl cluster
    0x0300: [DeviceCapability.COLOR, DeviceCapability.COLOR_TEMP],
}
