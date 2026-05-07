"""Core abstractions: devices, adapters, registry, state, scenes, errors."""

from logicahome.core.adapter import Adapter, AdapterError
from logicahome.core.device import Device, DeviceCapability, DeviceState
from logicahome.core.errors import ErrorCode, StructuredError
from logicahome.core.registry import Registry
from logicahome.core.scene import Scene, SceneAction

__all__ = [
    "Adapter",
    "AdapterError",
    "Device",
    "DeviceCapability",
    "DeviceState",
    "ErrorCode",
    "Registry",
    "Scene",
    "SceneAction",
    "StructuredError",
]
