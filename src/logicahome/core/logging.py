"""Structured logging — opt-in, via stdlib + LOGICAHOME_LOG_LEVEL env."""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def get_logger(name: str = "logicahome") -> logging.Logger:
    """Return a configured logger.

    Activated by `LOGICAHOME_LOG_LEVEL` env var (default: WARNING). Logs go
    to stderr so MCP stdio (stdout) stays clean.
    """
    global _CONFIGURED
    if not _CONFIGURED:
        level = os.environ.get("LOGICAHOME_LOG_LEVEL", "WARNING").upper()
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
        root = logging.getLogger("logicahome")
        root.setLevel(level)
        root.addHandler(handler)
        root.propagate = False
        _CONFIGURED = True
    return logging.getLogger(name)
