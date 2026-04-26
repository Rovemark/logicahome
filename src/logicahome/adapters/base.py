"""Adapter loader. Maps adapter names to implementations.

Adding a new adapter is a two-step change:
  1. Implement Adapter in `src/logicahome/adapters/<name>.py`
  2. Register it in ADAPTERS below
"""

from __future__ import annotations

from typing import Any

from logicahome.core.adapter import Adapter

ADAPTERS: dict[str, str] = {
    "tuya": "logicahome.adapters.tuya:TuyaAdapter",
    "home_assistant": "logicahome.adapters.home_assistant:HomeAssistantAdapter",
}


def registered_adapters() -> list[str]:
    return list(ADAPTERS.keys())


def load_adapter(name: str, config: dict[str, Any] | None = None) -> Adapter:
    if name not in ADAPTERS:
        raise ValueError(f"Unknown adapter: {name}. Available: {registered_adapters()}")
    module_path, class_name = ADAPTERS[name].split(":")
    import importlib

    module = importlib.import_module(module_path)
    cls: type[Adapter] = getattr(module, class_name)
    return cls(config=config)
