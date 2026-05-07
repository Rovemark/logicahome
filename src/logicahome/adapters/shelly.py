"""Shelly adapter — local HTTP for Shelly Gen1 and Gen2 devices.

Configuration:
    adapters:
      shelly:
        devices:
          - ip: 192.168.0.30
            name: "Hall plug"
            gen: 1            # 1 (Plus/Plug S Gen1) or 2 (Plus/Pro Gen2)
            channel: 0        # relay/switch index, default 0

Gen1 uses a flat REST API (`/relay/0?turn=on`).
Gen2 uses JSON-RPC (`/rpc/Switch.Set`).

Both run entirely on the LAN — no Shelly cloud required.
"""

from __future__ import annotations

from typing import Any

import aiohttp

from logicahome.core.adapter import Adapter
from logicahome.core.device import Device, DeviceCapability, DeviceState


class ShellyAdapter(Adapter):
    name = "shelly"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._session: aiohttp.ClientSession | None = None

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def discover(self) -> list[Device]:
        out: list[Device] = []
        for d in self.config.get("devices", []):
            out.append(
                Device(
                    slug=d.get("slug") or _slugify(d["name"]),
                    name=d["name"],
                    adapter="shelly",
                    native_id=d["ip"],
                    capabilities=[DeviceCapability.ON_OFF, DeviceCapability.POWER_METERING],
                    room=d.get("room"),
                    manufacturer="Shelly",
                    model=d.get("model"),
                    metadata={
                        "ip": d["ip"],
                        "gen": int(d.get("gen", 2)),
                        "channel": int(d.get("channel", 0)),
                    },
                )
            )
        return out

    async def get_state(self, device: Device) -> DeviceState:
        ip = device.metadata["ip"]
        gen = device.metadata["gen"]
        channel = device.metadata["channel"]
        session = await self._http()
        if gen == 1:
            async with session.get(f"http://{ip}/relay/{channel}") as resp:
                resp.raise_for_status()
                data = await resp.json()
            return DeviceState(on=data.get("ison"), extra={"raw": data})
        async with session.get(f"http://{ip}/rpc/Switch.GetStatus", params={"id": channel}) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return DeviceState(
            on=data.get("output"),
            power_w=data.get("apower"),
            extra={"raw": data},
        )

    async def set_state(self, device: Device, **changes: Any) -> DeviceState:
        if "on" not in changes:
            return await self.get_state(device)
        ip = device.metadata["ip"]
        gen = device.metadata["gen"]
        channel = device.metadata["channel"]
        session = await self._http()
        if gen == 1:
            turn = "on" if changes["on"] else "off"
            async with session.get(f"http://{ip}/relay/{channel}", params={"turn": turn}) as resp:
                resp.raise_for_status()
        else:
            async with session.post(
                f"http://{ip}/rpc/Switch.Set",
                json={"id": channel, "on": bool(changes["on"])},
            ) as resp:
                resp.raise_for_status()
        return await self.get_state(device)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")
