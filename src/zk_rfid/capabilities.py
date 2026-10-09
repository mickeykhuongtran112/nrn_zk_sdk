"""Declared wire capabilities are not inferred hardware verification."""

from dataclasses import dataclass
from .errors import UnsupportedFeature, UnverifiedFeature, ValidationError
from .models import boolean, integer


@dataclass(frozen=True)
class ReaderCapabilities:
    antenna_ports: int = 1
    model: str | None = None
    firmware: str | None = None
    ex10: bool = True
    realtime: bool = True
    gpio: bool = True
    temperature: bool = True
    # 0x94 echo is supported by previous DLL/reader traces, not typo 0x51.
    power_response_command: int = 0x94
    # Errata require explicit selection; do not pad to the summary's 10 bytes.
    cfg25_length: int | None = None
    cfg29_length: int | None = None
    # Buffer mask width on 16-port devices contradicts the prose in V2.25.
    buffer_antenna_bytes: int | None = None
    hardware_verified: bool = False
    evidence: str = "V2.25 documented contract; deployment must confirm module/firmware"

    def __post_init__(self):
        integer(self.antenna_ports, 1, 16, "antenna_ports")
        if self.antenna_ports not in (1, 4, 8, 16):
            raise ValidationError("Documented layouts are for 1, 4, 8, 16 ports")
        for name in ("ex10", "realtime", "gpio", "temperature", "hardware_verified"):
            boolean(getattr(self, name), name)
        if self.power_response_command != 0x94:
            raise UnverifiedFeature(
                "0x51 power response conflicts with fast-stop; use verified 0x94"
            )
        if self.cfg25_length not in (None, 6) or self.cfg29_length not in (None, 5):
            raise UnverifiedFeature("Only detailed CFG25=6/CFG29=5 field layouts are implemented")
        if self.buffer_antenna_bytes not in (None, 1, 2):
            raise ValidationError("buffer_antenna_bytes must be None, 1 or 2")

    def require(self, feature: str) -> None:
        if feature not in ("ex10", "realtime", "gpio", "temperature"):
            raise UnsupportedFeature(f"Unknown capability: {feature}")
        if not getattr(self, feature):
            raise UnsupportedFeature(f"{feature} is disabled by the selected capabilities")
