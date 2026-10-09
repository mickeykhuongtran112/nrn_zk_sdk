"""Vendor phase convention and explicitly user-defined RSSI mapping."""

import math
from .errors import ValidationError

PHASE_CONVERSION = "ex10_v6_8_demo_0.087deg_mod180"
RSSI_SOURCE = "user_linear_raw_minus_135"


def rssi_to_dbm(raw: int) -> float:
    """User-defined linear mapping: raw 60 -> -75 dBm, 110 -> -25 dBm.

    This is an estimate chosen by the user, not a vendor-calibrated reading.
    All uint8 values use raw - 135; outside 60..110 this extrapolates without
    clamping. Decoded reports retain raw, source and an in-range flag.
    """
    if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= 255:
        raise ValidationError("RSSI must be a uint8 integer")
    return float(raw - 135)


def _rssi_fields(raw: int) -> dict:
    """Apply the same mapping and provenance to every wire report format."""
    return {
        "rssi_raw": raw,
        "rssi_dbm": rssi_to_dbm(raw),
        "rssi_source": RSSI_SOURCE,
        "rssi_in_calibration_range": 60 <= raw <= 110,
    }


def phase_to_degrees(raw: int, *, wrap: bool = True) -> float:
    """Convert one uint16 phase word using Form1.cs's 0.087 deg/tick.

    By default fold into [0, 180), matching the vendor's normal inventory
    display. wrap=False returns the scaled word without folding. This is
    a vendor display convention, not evidence of calibrated absolute phase.
    """
    if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= 65535:
        raise ValidationError("phase must be a uint16 integer")
    if not isinstance(wrap, bool):
        raise ValidationError("wrap must be boolean")
    degrees = raw * 0.087
    return degrees % 180 if wrap else degrees


def phase_to_radians(raw: int, *, wrap: bool = True) -> float:
    """Radians of phase_to_degrees; folded values are in [0, pi)."""
    return math.radians(phase_to_degrees(raw, wrap=wrap))
