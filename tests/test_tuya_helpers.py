"""Pure-function tests for the Tuya adapter helpers.

These don't require tinytuya at all — they exercise the DPS<->DeviceState
translation and the HSV<->RGB color encoding that Tuya bulbs use.
"""

from __future__ import annotations

import pytest

pytest.importorskip("tinytuya", reason="tinytuya extra required for adapter import")

from logicahome.adapters.tuya import (  # noqa: E402
    DEFAULT_DPS,
    _dps_to_state,
    _rgb_to_tuya_hsv_hex,
    _tuya_hsv_hex_to_rgb,
)


def test_dps_to_state_on_with_brightness() -> None:
    state = _dps_to_state({"1": True, "2": 505}, DEFAULT_DPS)
    assert state.on is True
    # 505 is roughly the midpoint of [10, 1000] -> ~50%
    assert state.brightness is not None
    assert 48 <= state.brightness <= 52


def test_dps_to_state_off() -> None:
    state = _dps_to_state({"1": False}, DEFAULT_DPS)
    assert state.on is False
    assert state.brightness is None


def test_dps_to_state_brightness_clamps() -> None:
    state_low = _dps_to_state({"2": 0}, DEFAULT_DPS)
    assert state_low.brightness == 0
    state_high = _dps_to_state({"2": 9999}, DEFAULT_DPS)
    assert state_high.brightness == 100


def test_dps_to_state_power_metering() -> None:
    state = _dps_to_state({"19": 1234}, DEFAULT_DPS)  # 123.4 W
    assert state.power_w == pytest.approx(123.4, rel=1e-3)


def test_rgb_roundtrip_red() -> None:
    hex_str = _rgb_to_tuya_hsv_hex(255, 0, 0)
    assert len(hex_str) == 12
    rgb = _tuya_hsv_hex_to_rgb(hex_str)
    assert rgb is not None
    r, g, b = rgb
    assert r >= 250
    assert g <= 5
    assert b <= 5


def test_rgb_roundtrip_white_ish() -> None:
    hex_str = _rgb_to_tuya_hsv_hex(200, 200, 200)
    rgb = _tuya_hsv_hex_to_rgb(hex_str)
    assert rgb is not None
    # HSV roundtrip on grey is approximate; allow 5-unit drift per channel
    for c, expected in zip(rgb, (200, 200, 200), strict=False):
        assert abs(c - expected) <= 5


def test_invalid_hex_returns_none() -> None:
    assert _tuya_hsv_hex_to_rgb("not-hex") is None
    assert _tuya_hsv_hex_to_rgb("") is None
    assert _tuya_hsv_hex_to_rgb("ZZZZZZZZZZZZ") is None
