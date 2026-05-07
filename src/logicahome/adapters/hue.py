"""Philips Hue adapter — local Hue Bridge REST API.

Configuration:
    adapters:
      hue:
        bridge_ip: 192.168.0.10
        api_key: <generated-by-bridge-button>

How to get an api_key (one-time):
    1. Press the link button on your Hue Bridge.
    2. Within 30 seconds: POST http://<bridge_ip>/api with body
       {"devicetype":"logicahome#user"} — bridge returns the api_key.
    3. The wizard `logicahome connect hue` automates this.

The bridge runs entirely on your LAN. No Hue cloud account required for
local control (cloud-only features like remote access are not used here).
"""

from __future__ import annotations

from typing import Any

import aiohttp

from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.device import Device, DeviceCapability, DeviceState


class HueAdapter(Adapter):
    name = "hue"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        if not self.config.get("bridge_ip"):
            raise AdapterError("hue adapter requires `bridge_ip` in config")
        if not self.config.get("api_key"):
            raise AdapterError(
                "hue adapter requires `api_key` in config — run `logicahome connect hue`"
            )
        self._session: aiohttp.ClientSession | None = None

    @property
    def _base_url(self) -> str:
        return f"http://{self.config['bridge_ip']}/api/{self.config['api_key']}"

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def discover(self) -> list[Device]:
        session = await self._http()
        async with session.get(f"{self._base_url}/lights") as resp:
            resp.raise_for_status()
            data = await resp.json()
        devices: list[Device] = []
        for native_id, info in data.items():
            caps = [DeviceCapability.ON_OFF]
            ctype = (info.get("type") or "").lower()
            if "dimmable" in ctype or "color" in ctype or "extended" in ctype:
                caps.append(DeviceCapability.BRIGHTNESS)
            if "color" in ctype:
                caps.extend([DeviceCapability.COLOR, DeviceCapability.COLOR_TEMP])
            devices.append(
                Device(
                    slug=f"hue-{native_id}",
                    name=info.get("name", f"Hue light {native_id}"),
                    adapter="hue",
                    native_id=str(native_id),
                    capabilities=caps,
                    manufacturer=info.get("manufacturername", "Philips"),
                    model=info.get("modelid"),
                    metadata={"type": info.get("type")},
                )
            )
        return devices

    async def get_state(self, device: Device) -> DeviceState:
        session = await self._http()
        async with session.get(f"{self._base_url}/lights/{device.native_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
        state = data.get("state", {})
        bri_raw = state.get("bri")
        return DeviceState(
            on=state.get("on"),
            brightness=round(bri_raw / 254 * 100) if bri_raw is not None else None,
            color_temp_kelvin=_mired_to_kelvin(state.get("ct")) if state.get("ct") else None,
            extra={"raw_state": state},
        )

    async def set_state(self, device: Device, **changes: Any) -> DeviceState:
        payload: dict[str, Any] = {}
        if "on" in changes:
            payload["on"] = bool(changes["on"])
        if "brightness" in changes:
            level = max(0, min(100, int(changes["brightness"])))
            payload["bri"] = round(level / 100 * 254)
            payload["on"] = level > 0
        if "color_rgb" in changes:
            payload["xy"] = _rgb_to_xy(*changes["color_rgb"])
        if "color_temp_kelvin" in changes:
            payload["ct"] = _kelvin_to_mired(int(changes["color_temp_kelvin"]))

        if not payload:
            return await self.get_state(device)

        session = await self._http()
        async with session.put(
            f"{self._base_url}/lights/{device.native_id}/state", json=payload
        ) as resp:
            resp.raise_for_status()
        return await self.get_state(device)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


def _mired_to_kelvin(mired: int) -> int:
    return round(1_000_000 / mired) if mired else 0


def _kelvin_to_mired(kelvin: int) -> int:
    return round(1_000_000 / kelvin) if kelvin else 0


def _rgb_to_xy(r: int, g: int, b: int) -> list[float]:
    """RGB (0-255) to CIE xy chromaticity, per Philips' wide-gamut formula."""
    rn, gn, bn = r / 255, g / 255, b / 255

    def gamma(c: float) -> float:
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92

    rg, gg, bg = gamma(rn), gamma(gn), gamma(bn)
    x = rg * 0.664511 + gg * 0.154324 + bg * 0.162028
    y = rg * 0.283881 + gg * 0.668433 + bg * 0.047685
    z = rg * 0.000088 + gg * 0.072310 + bg * 0.986039
    total = x + y + z or 1.0
    return [round(x / total, 4), round(y / total, 4)]
