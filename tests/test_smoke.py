"""Smoke tests — verify the package imports and the registry roundtrips."""

from __future__ import annotations

from pathlib import Path

import pytest

from logicahome import __version__
from logicahome.core.device import Device, DeviceCapability
from logicahome.core.registry import Registry


def test_version() -> None:
    assert __version__


def test_adapters_register() -> None:
    from logicahome.adapters import registered_adapters

    names = registered_adapters()
    assert "tuya" in names
    assert "home_assistant" in names


@pytest.mark.asyncio
async def test_registry_roundtrip(tmp_path: Path) -> None:
    registry = Registry(db_path=tmp_path / "test.db")
    await registry.initialize()

    device = Device(
        slug="test-lamp",
        name="Test lamp",
        adapter="tuya",
        native_id="bf-test",
        capabilities=[DeviceCapability.ON_OFF, DeviceCapability.BRIGHTNESS],
        room="lab",
    )
    await registry.upsert(device)

    fetched = await registry.get("test-lamp")
    assert fetched is not None
    assert fetched.name == "Test lamp"
    assert DeviceCapability.BRIGHTNESS in fetched.capabilities

    all_devices = await registry.list_all()
    assert len(all_devices) == 1

    removed = await registry.remove("test-lamp")
    assert removed is True
    assert await registry.get("test-lamp") is None


def test_mcp_server_imports() -> None:
    """The MCP server module must import even if mcp client never connects."""
    from logicahome import server

    assert server.server is not None
