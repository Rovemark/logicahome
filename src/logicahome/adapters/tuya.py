"""Tuya / SmartLife adapter — local LAN protocol, no cloud required.

Configuration (in config.yaml):
    adapters:
      tuya:
        devices:
          - id: bf12345...        # device_id from Tuya
            ip: 192.168.0.42
            local_key: <key>
            version: "3.4"
            name: "Sala — luminária"
            capabilities: [on_off, brightness]
            # Optional: override the default DPS mapping for non-standard devices
            # dps_map:
            #   on_off: "1"
            #   brightness: "2"
            #   color_temp: "3"
            #   color_rgb: "5"

The local_key is obtained once via the `logicahome connect tuya` wizard,
which delegates to the official tinytuya cloud login. After that, no
internet is required.

tinytuya is a synchronous library, so adapter calls run inside
`asyncio.to_thread` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.device import Device, DeviceCapability, DeviceState

if TYPE_CHECKING:
    pass


# Default Tuya DPS (Data Point) numbers. These cover ~90% of Tuya devices.
# Per-device overrides go in config under `dps_map`.
DEFAULT_DPS = {
    "on_off": "1",
    "brightness": "2",
    "color_temp": "3",
    "color_rgb": "5",
    "power_w": "19",
    "voltage_v": "20",
    "current_ma": "18",
}

# Tuya brightness range. Most devices use 10-1000; we expose 0-100 to users.
TUYA_BRIGHTNESS_MIN = 10
TUYA_BRIGHTNESS_MAX = 1000


class TuyaAdapter(Adapter):
    name = "tuya"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        try:
            import tinytuya as _t  # noqa: F401
        except ImportError as e:
            raise AdapterError("tinytuya not installed. Run: pip install 'logicahome[tuya]'") from e
        self._tinytuya: Any = _t

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
                        "version": str(d.get("version", "3.4")),
                        "local_key": d["local_key"],
                        "dps_map": {**DEFAULT_DPS, **d.get("dps_map", {})},
                    },
                )
            )
        return result

    async def get_state(self, device: Device) -> DeviceState:
        dps = await asyncio.to_thread(self._read_dps, device)
        return _dps_to_state(dps, device.metadata["dps_map"])

    async def set_state(self, device: Device, **changes: Any) -> DeviceState:
        await asyncio.to_thread(self._apply_changes, device, changes)
        return await self.get_state(device)

    async def close(self) -> None:
        return None

    # --- sync helpers (run inside asyncio.to_thread) -----------------------

    def _outlet(self, device: Device) -> Any:
        meta = device.metadata
        outlet = self._tinytuya.OutletDevice(
            device.native_id,
            meta["ip"],
            meta["local_key"],
        )
        outlet.set_version(float(meta["version"]))
        outlet.set_socketTimeout(5)
        return outlet

    def _read_dps(self, device: Device) -> dict[str, Any]:
        outlet = self._outlet(device)
        try:
            data = outlet.status()
        except Exception as e:
            raise AdapterError(f"Tuya status() failed for {device.slug}: {e}") from e
        if isinstance(data, dict) and "Error" in data:
            raise AdapterError(f"Tuya error for {device.slug}: {data.get('Error')}")
        return (data or {}).get("dps", {}) if isinstance(data, dict) else {}

    def _apply_changes(self, device: Device, changes: dict[str, Any]) -> None:
        outlet = self._outlet(device)
        dps_map = device.metadata["dps_map"]
        payload: dict[str, Any] = {}

        if "on" in changes:
            payload[dps_map["on_off"]] = bool(changes["on"])

        if "brightness" in changes:
            level = max(0, min(100, int(changes["brightness"])))
            tuya_value = round(
                TUYA_BRIGHTNESS_MIN + (level / 100) * (TUYA_BRIGHTNESS_MAX - TUYA_BRIGHTNESS_MIN)
            )
            payload[dps_map["brightness"]] = tuya_value

        if "color_rgb" in changes:
            r, g, b = changes["color_rgb"]
            payload[dps_map["color_rgb"]] = _rgb_to_tuya_hsv_hex(r, g, b)

        if "color_temp_kelvin" in changes:
            payload[dps_map["color_temp"]] = int(changes["color_temp_kelvin"])

        if not payload:
            return

        try:
            outlet.set_multiple_values(payload, nowait=False)
        except AttributeError:
            # Older tinytuya: fall back to one-by-one
            for dps, value in payload.items():
                with contextlib.suppress(Exception):
                    outlet.set_value(dps, value, nowait=False)
        except Exception as e:
            raise AdapterError(f"Tuya set failed for {device.slug}: {e}") from e


# --- pure helpers ----------------------------------------------------------


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("—", "-").replace("/", "-")


def _dps_to_state(dps: dict[str, Any], dps_map: dict[str, str]) -> DeviceState:
    """Translate Tuya DPS dict to our canonical DeviceState."""
    on = dps.get(dps_map.get("on_off", "1"))
    brightness_raw = dps.get(dps_map.get("brightness", "2"))
    brightness = None
    if brightness_raw is not None:
        try:
            raw_int = int(brightness_raw)
            brightness = round(
                (raw_int - TUYA_BRIGHTNESS_MIN) / (TUYA_BRIGHTNESS_MAX - TUYA_BRIGHTNESS_MIN) * 100
            )
            brightness = max(0, min(100, brightness))
        except (TypeError, ValueError):
            brightness = None

    rgb_hex = dps.get(dps_map.get("color_rgb", "5"))
    rgb = _tuya_hsv_hex_to_rgb(rgb_hex) if rgb_hex else None

    color_temp = dps.get(dps_map.get("color_temp", "3"))

    power_w_raw = dps.get(dps_map.get("power_w", "19"))
    power_w = None
    if power_w_raw is not None:
        try:
            power_w = float(power_w_raw) / 10  # Tuya reports power in deciwatts
        except (TypeError, ValueError):
            power_w = None

    return DeviceState(
        on=bool(on) if on is not None else None,
        brightness=brightness,
        color_rgb=rgb,
        color_temp_kelvin=int(color_temp) if isinstance(color_temp, (int, float)) else None,
        power_w=power_w,
        extra={"raw_dps": dps},
    )


def _rgb_to_tuya_hsv_hex(r: int, g: int, b: int) -> str:
    """Convert RGB (0-255) to the 12-char HSV hex Tuya expects."""
    import colorsys

    rn, gn, bn = r / 255, g / 255, b / 255
    h, s, v = colorsys.rgb_to_hsv(rn, gn, bn)
    h_int = int(h * 360)
    s_int = int(s * 1000)
    v_int = int(v * 1000)
    return f"{h_int:04x}{s_int:04x}{v_int:04x}"


def _tuya_hsv_hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    if not isinstance(hex_str, str) or len(hex_str) != 12:
        return None
    try:
        h = int(hex_str[0:4], 16)
        s = int(hex_str[4:8], 16)
        v = int(hex_str[8:12], 16)
    except ValueError:
        return None
    import colorsys

    r, g, b = colorsys.hsv_to_rgb(h / 360, s / 1000, v / 1000)
    return (round(r * 255), round(g * 255), round(b * 255))
