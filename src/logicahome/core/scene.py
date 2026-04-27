"""Scene model — a snapshot of state across multiple devices.

Scenes are how LogicaHome turns "modo dormir" into a single tool call.
Each scene names a list of `SceneAction` items, one per affected device.
The runtime applies them concurrently when the scene runs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SceneAction(BaseModel):
    """One device's contribution to a scene."""

    device_slug: str
    on: bool | None = None
    brightness: int | None = Field(default=None, ge=0, le=100)
    color_rgb: tuple[int, int, int] | None = None
    color_temp_kelvin: int | None = None

    def to_changes(self) -> dict[str, Any]:
        """Convert to the **kwargs runtime.set_state expects."""
        out: dict[str, Any] = {}
        if self.on is not None:
            out["on"] = self.on
        if self.brightness is not None:
            out["brightness"] = self.brightness
        if self.color_rgb is not None:
            out["color_rgb"] = self.color_rgb
        if self.color_temp_kelvin is not None:
            out["color_temp_kelvin"] = self.color_temp_kelvin
        return out


class Scene(BaseModel):
    """A named, reusable group of device actions."""

    slug: str
    name: str
    description: str | None = None
    actions: list[SceneAction]
