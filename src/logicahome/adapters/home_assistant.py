"""Home Assistant adapter — bridges into an existing HA install via REST API.

Configuration:
    adapters:
      home_assistant:
        url: http://homeassistant.local:8123
        token: <long-lived-access-token>
        include_domains: [light, switch, climate, sensor]
"""

from __future__ import annotations

from typing import Any

import aiohttp

from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.device import Device, DeviceCapability, DeviceState

DOMAIN_CAPS: dict[str, list[DeviceCapability]] = {
    "light": [DeviceCapability.ON_OFF, DeviceCapability.BRIGHTNESS, DeviceCapability.COLOR],
    "switch": [DeviceCapability.ON_OFF],
    "climate": [DeviceCapability.TEMPERATURE, DeviceCapability.TEMPERATURE_SET],
    "lock": [DeviceCapability.LOCK],
    "cover": [DeviceCapability.COVER],
    "fan": [DeviceCapability.ON_OFF, DeviceCapability.FAN_SPEED],
    "media_player": [DeviceCapability.MEDIA_PLAY, DeviceCapability.MEDIA_VOLUME],
    "binary_sensor": [DeviceCapability.MOTION, DeviceCapability.CONTACT],
    "sensor": [],
    "scene": [DeviceCapability.SCENE],
}


class HomeAssistantAdapter(Adapter):
    name = "home_assistant"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        if not self.config.get("url"):
            raise AdapterError("home_assistant adapter requires `url` in config")
        if not self.config.get("token"):
            raise AdapterError("home_assistant adapter requires `token` in config")
        self._session: aiohttp.ClientSession | None = None

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.config['token']}",
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def discover(self) -> list[Device]:
        include = set(self.config.get("include_domains", DOMAIN_CAPS.keys()))
        session = await self._http()
        async with session.get(f"{self.config['url']}/api/states") as resp:
            resp.raise_for_status()
            states = await resp.json()

        devices: list[Device] = []
        for s in states:
            entity_id: str = s["entity_id"]
            domain = entity_id.split(".", 1)[0]
            if domain not in include:
                continue
            attrs = s.get("attributes", {})
            devices.append(
                Device(
                    slug=entity_id.replace(".", "-"),
                    name=attrs.get("friendly_name", entity_id),
                    adapter="home_assistant",
                    native_id=entity_id,
                    capabilities=DOMAIN_CAPS.get(domain, []),
                    room=attrs.get("area_id"),
                    metadata={"domain": domain},
                )
            )
        return devices

    async def get_state(self, device: Device) -> DeviceState:
        session = await self._http()
        async with session.get(f"{self.config['url']}/api/states/{device.native_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
        return _parse_ha_state(data)

    async def set_state(self, device: Device, **changes: Any) -> DeviceState:
        domain = device.metadata.get("domain", device.native_id.split(".", 1)[0])
        service = _ha_service_for(domain, changes)
        if service is None:
            raise AdapterError(f"No HA service for changes={changes} on {device.slug}")
        session = await self._http()
        payload: dict[str, Any] = {"entity_id": device.native_id}
        if "brightness" in changes:
            payload["brightness_pct"] = changes["brightness"]
        if "color_rgb" in changes:
            payload["rgb_color"] = list(changes["color_rgb"])
        if "color_temp_kelvin" in changes:
            payload["kelvin"] = int(changes["color_temp_kelvin"])
        if "target_temperature_c" in changes:
            payload["temperature"] = float(changes["target_temperature_c"])
        if "media_volume" in changes:
            payload["volume_level"] = max(0, min(100, int(changes["media_volume"]))) / 100
        if "cover_position" in changes:
            payload["position"] = max(0, min(100, int(changes["cover_position"])))
        if "fan_speed" in changes:
            payload["percentage"] = max(0, min(100, int(changes["fan_speed"])))
        async with session.post(
            f"{self.config['url']}/api/services/{domain}/{service}",
            json=payload,
        ) as resp:
            resp.raise_for_status()
        return await self.get_state(device)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


def _ha_service_for(domain: str, changes: dict[str, Any]) -> str | None:
    if domain == "lock":
        if "locked" in changes:
            return "lock" if changes["locked"] else "unlock"
        return None
    if domain == "cover":
        if "cover_position" in changes:
            return "set_cover_position"
        if "on" in changes:
            return "open_cover" if changes["on"] else "close_cover"
        return None
    if domain == "climate":
        if "target_temperature_c" in changes:
            return "set_temperature"
        return None
    if domain == "media_player":
        if "media_volume" in changes:
            return "volume_set"
        if "media_playing" in changes:
            return "media_play" if changes["media_playing"] else "media_pause"
        return None
    if domain == "fan" and "fan_speed" in changes:
        return "set_percentage"
    if "on" in changes:
        return "turn_on" if changes["on"] else "turn_off"
    if "brightness" in changes or "color_rgb" in changes or "color_temp_kelvin" in changes:
        return "turn_on"
    return None


def _parse_ha_state(data: dict[str, Any]) -> DeviceState:
    state = data.get("state")
    attrs = data.get("attributes", {})
    on = (
        state in {"on", "open", "unlocked"}
        if state in {"on", "off", "open", "closed", "locked", "unlocked"}
        else None
    )
    brightness = attrs.get("brightness")
    if brightness is not None:
        brightness = round(brightness / 255 * 100)
    rgb = attrs.get("rgb_color")
    volume = attrs.get("volume_level")
    return DeviceState(
        on=on,
        brightness=brightness,
        color_rgb=tuple(rgb) if rgb else None,
        color_temp_kelvin=attrs.get("color_temp_kelvin"),
        temperature_c=attrs.get("current_temperature") or attrs.get("temperature"),
        target_temperature_c=attrs.get("temperature"),
        humidity_pct=attrs.get("humidity"),
        locked=(state == "locked") if state in {"locked", "unlocked"} else None,
        media_playing=(state == "playing") if state in {"playing", "paused", "idle"} else None,
        media_volume=round(volume * 100) if volume is not None else None,
        cover_position=attrs.get("current_position"),
        fan_speed=attrs.get("percentage"),
        extra={"raw_state": state},
    )
