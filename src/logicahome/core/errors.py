"""Structured error model.

When an adapter or runtime call fails, we want the AI client to recover —
not parse a free-form traceback. Errors carry a stable code, a human
message, optional remediation, and the entity that failed.

Convert any exception to a `StructuredError` via `from_exception` so the
MCP server can serialize it consistently.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    DEVICE_NOT_FOUND = "device_not_found"
    SCENE_NOT_FOUND = "scene_not_found"
    ADAPTER_NOT_CONFIGURED = "adapter_not_configured"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    DEVICE_OFFLINE = "device_offline"
    AUTH_FAILED = "auth_failed"
    TIMEOUT = "timeout"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    INVALID_INPUT = "invalid_input"
    INTERNAL_ERROR = "internal_error"


class StructuredError(BaseModel):
    """Stable error envelope returned by tools and CLI."""

    code: ErrorCode
    message: str
    fix: str | None = None
    device_slug: str | None = None
    scene_slug: str | None = None
    adapter: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_exception(cls, exc: BaseException, **context: Any) -> StructuredError:
        """Best-effort mapping from a raw exception to a StructuredError."""
        from logicahome.core.adapter import AdapterError

        msg = str(exc) or exc.__class__.__name__
        msg_lower = msg.lower()

        if isinstance(exc, TimeoutError) or "timeout" in msg_lower:
            return cls(
                code=ErrorCode.TIMEOUT,
                message=msg,
                fix="Check the device is reachable on the network and increase LOGICAHOME_TIMEOUT_S if needed.",
                **context,
            )
        if "unauthorized" in msg_lower or "401" in msg_lower or "403" in msg_lower:
            return cls(
                code=ErrorCode.AUTH_FAILED,
                message=msg,
                fix="Re-run `logicahome connect <adapter>` to refresh credentials.",
                **context,
            )
        if "not configured" in msg_lower:
            return cls(
                code=ErrorCode.ADAPTER_NOT_CONFIGURED,
                message=msg,
                fix="Run `logicahome connect <adapter>` to configure it.",
                **context,
            )
        if "unknown device" in msg_lower:
            return cls(
                code=ErrorCode.DEVICE_NOT_FOUND,
                message=msg,
                fix="Run `logicahome discover` then `logicahome device list` to see known slugs.",
                **context,
            )
        if "unknown scene" in msg_lower:
            return cls(
                code=ErrorCode.SCENE_NOT_FOUND,
                message=msg,
                fix="Run `logicahome scene list` to see known scene slugs.",
                **context,
            )
        if isinstance(exc, AdapterError):
            return cls(
                code=ErrorCode.ADAPTER_UNAVAILABLE,
                message=msg,
                fix="Check the adapter's configuration and that the device is online.",
                **context,
            )
        return cls(code=ErrorCode.INTERNAL_ERROR, message=msg, **context)
