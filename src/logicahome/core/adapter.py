"""Adapter contract — the smallest unit of contribution to LogicaHome.

Every smart-home ecosystem (Tuya, Home Assistant, Google Home, Matter, ...)
gets one adapter. An adapter implements four async methods. Nothing else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from logicahome.core.device import Device, DeviceState


class AdapterError(Exception):
    """Raised when an adapter cannot complete an operation."""


class Adapter(ABC):
    """Abstract base for all device-ecosystem adapters."""

    name: str = ""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    async def discover(self) -> list[Device]:
        """Scan the network/cloud and return all devices this adapter can control."""

    @abstractmethod
    async def get_state(self, device: Device) -> DeviceState:
        """Fetch current state of a device."""

    @abstractmethod
    async def set_state(self, device: Device, **changes: Any) -> DeviceState:
        """Apply state changes (e.g. on=True, brightness=50). Returns new state."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources (sockets, sessions, etc)."""

    async def __aenter__(self) -> Adapter:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
