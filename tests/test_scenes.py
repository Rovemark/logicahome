"""Scene model + registry roundtrip tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from logicahome.core.registry import Registry
from logicahome.core.scene import Scene, SceneAction


def test_scene_action_to_changes_filters_none() -> None:
    action = SceneAction(device_slug="lamp", on=True, brightness=40)
    assert action.to_changes() == {"on": True, "brightness": 40}


def test_scene_action_to_changes_color() -> None:
    action = SceneAction(device_slug="lamp", on=True, color_rgb=(255, 0, 0))
    assert action.to_changes() == {"on": True, "color_rgb": (255, 0, 0)}


def test_scene_action_brightness_clamps_via_pydantic() -> None:
    with pytest.raises(ValidationError):
        SceneAction(device_slug="lamp", brightness=150)


@pytest.mark.asyncio
async def test_scene_registry_roundtrip(tmp_path: Path) -> None:
    registry = Registry(db_path=tmp_path / "test.db")
    await registry.initialize()

    scene = Scene(
        slug="bedtime",
        name="Bedtime",
        description="Lights low, TV off.",
        actions=[
            SceneAction(device_slug="bedroom-lamp", on=True, brightness=10),
            SceneAction(device_slug="living-room-tv", on=False),
        ],
    )
    await registry.upsert_scene(scene)

    fetched = await registry.get_scene("bedtime")
    assert fetched is not None
    assert fetched.name == "Bedtime"
    assert len(fetched.actions) == 2
    assert fetched.actions[0].device_slug == "bedroom-lamp"
    assert fetched.actions[0].brightness == 10

    all_scenes = await registry.list_scenes()
    assert len(all_scenes) == 1

    removed = await registry.remove_scene("bedtime")
    assert removed is True
    assert await registry.get_scene("bedtime") is None
