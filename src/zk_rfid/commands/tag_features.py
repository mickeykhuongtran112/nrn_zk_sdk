"""Vendor tag commands are explicitly outside the default Gen2 SDK contract.

NXP read-protection/EAS, Monza QT and EM4325 commands need an identified tag
and dedicated evidence. Presence of an Ex10 radio does not prove tag support.
FastID and TagFocus are exposed by inventory/extended with this same caveat.
"""

from ..errors import UnsupportedFeature

VENDOR_TAG_COMMANDS = {
    "nxp_read_protection": (0x08, 0x09, 0x0A, 0x0B),
    "nxp_eas": (0x0C, 0x0D),
    "monza_qt": (0x11, 0x12, 0x1B, 0x3A, 0x7D, 0x7E),
    "em4325": (0x85, 0x86, 0x87, 0x88),
}


def require_vendor_feature(feature: str) -> None:
    raise UnsupportedFeature(
        f"{feature}: vendor tag extension requires a separate validated contract"
    )
