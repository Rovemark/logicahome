"""Light-touch i18n — keyed phrases the CLI uses.

Switch the active language with the `LOGICAHOME_LANG` env var (e.g.
`en`, `pt`). Defaults to `en`. Missing keys fall back to English.

We deliberately avoid gettext + .po files until we have real demand
across more than two locales — keeping all strings in one Python dict
means contributors can add a language in one PR without learning a
toolchain.
"""

from __future__ import annotations

import os

PHRASES: dict[str, dict[str, str]] = {
    "en": {
        "no_devices": "No devices yet.",
        "no_scenes": "No scenes yet.",
        "saved": "Saved.",
        "config_created": "Created config at",
        "found_n_devices": "Found {n} device(s).",
        "validation_failed": "Validation failed",
        "ha_responded": "HA responded",
        "no_adapters": "No adapters configured.",
    },
    "pt": {
        "no_devices": "Nenhum dispositivo ainda.",
        "no_scenes": "Nenhuma cena ainda.",
        "saved": "Salvo.",
        "config_created": "Configuração criada em",
        "found_n_devices": "{n} dispositivo(s) encontrado(s).",
        "validation_failed": "Falha na validação",
        "ha_responded": "HA respondeu",
        "no_adapters": "Nenhum adapter configurado.",
    },
}


def _lang() -> str:
    raw = os.environ.get("LOGICAHOME_LANG", "en").lower()
    return raw.split("_")[0].split("-")[0]


def t(key: str, **kwargs: object) -> str:
    """Return the translated phrase for the active language."""
    table = PHRASES.get(_lang()) or PHRASES["en"]
    template = table.get(key) or PHRASES["en"].get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
