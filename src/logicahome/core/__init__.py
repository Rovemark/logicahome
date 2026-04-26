"""Core abstractions: devices, adapters, registry, state."""

from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.device import Device, DeviceCapability, DeviceState
from logicahome.core.registry import Registry

__all__ = [
    "Adapter",
    "AdapterError",
    "Device",
    "DeviceCapability",
    "DeviceState",
    "Registry",
]
