"""Device model — the canonical representation of anything controllable."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DeviceCapability(StrEnum):
    """What a device can do. Capabilities drive which MCP tools apply."""

    ON_OFF = "on_off"
    BRIGHTNESS = "brightness"
    COLOR = "color"
    COLOR_TEMP = "color_temp"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    MOTION = "motion"
    CONTACT = "contact"
    LOCK = "lock"
    POWER_METERING = "power_metering"
    SCENE = "scene"


class DeviceState(BaseModel):
    """Current state of a device. Adapters return this on get_state."""

    on: bool | None = None
    brightness: int | None = Field(default=None, ge=0, le=100)
    color_rgb: tuple[int, int, int] | None = None
    color_temp_kelvin: int | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    motion: bool | None = None
    contact_open: bool | None = None
    locked: bool | None = None
    power_w: float | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class Device(BaseModel):
    """A controllable thing in the home.

    Identity is (adapter, native_id) — the adapter knows how to talk to
    its own native_id. The user-facing id is `slug`.
    """

    slug: str
    name: str
    adapter: str
    native_id: str
    capabilities: list[DeviceCapability]
    room: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def supports(self, capability: DeviceCapability) -> bool:
        return capability in self.capabilities
