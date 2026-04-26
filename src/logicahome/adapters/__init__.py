"""Adapters — one per smart-home ecosystem."""

from logicahome.adapters.base import load_adapter, registered_adapters

__all__ = ["load_adapter", "registered_adapters"]
