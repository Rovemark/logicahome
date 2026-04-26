"""User configuration loader. YAML at ~/.config/logicahome/config.yaml (or platform equivalent)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir


def config_path() -> Path:
    path = Path(user_config_dir("logicahome", appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path / "config.yaml"


def load_config() -> dict[str, Any]:
    p = config_path()
    if not p.exists():
        return {"adapters": {}}
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"adapters": {}}


def save_config(config: dict[str, Any]) -> None:
    with config_path().open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
