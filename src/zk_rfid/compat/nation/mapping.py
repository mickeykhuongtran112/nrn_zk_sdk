"""Explicit value conversions. RF IDs, RSSI and phase are never guessed."""

from dataclasses import dataclass
from enum import Enum
from ...errors import UnverifiedFeature, UnsupportedFeature, ValidationError
from ...models import TagReport, integer


class Equivalence(str, Enum):
    VERIFIED = "verified-equivalent"
    CONVERTED = "converted"
    MULTI_STEP = "multi-step"
    APPROXIMATE = "approximate-with-conditions"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"


CONTRACT = {
    "reader_info": Equivalence.CONVERTED,
    "power": Equivalence.MULTI_STEP,
    "antenna_mask": Equivalence.CONVERTED,
    "inventory": Equivalence.CONVERTED,
    "epc_write": Equivalence.MULTI_STEP,
    "memory": Equivalence.CONVERTED,
    "rf_profile": Equivalence.UNVERIFIED,
    "rf_band": Equivalence.UNVERIFIED,
    "rssi_dbm": Equivalence.APPROXIMATE,
    "phase_radians": Equivalence.UNVERIFIED,
    "beeper_query": Equivalence.UNSUPPORTED,
    "native_filter": Equivalence.UNSUPPORTED,
}


@dataclass(frozen=True)
class RFMapping:
    """Caller-supplied, measured mapping, specific to both firmwares."""

    nation_id: int
    zk_id: int
    evidence: str
    confirmed: bool = False

    def require(self, nation_id: int) -> int:
        if not self.confirmed or not self.evidence.strip() or nation_id != self.nation_id:
            raise UnverifiedFeature("An explicit confirmed RF mapping with evidence is required")
        return integer(self.zk_id, 0, 65535, "native profile ID")


def hex_epc(value: str) -> bytes:
    if not isinstance(value, str) or not value or len(value) % 4:
        raise ValidationError("EPC hex must contain whole 16-bit words")
    if any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValidationError("EPC hex must not contain separators or non-hex digits")
    data = bytes.fromhex(value)
    if len(data) > 62:
        raise ValidationError("EPC exceeds 31 words")
    return data


def power_dict(powers: tuple[int, ...]) -> dict[int, int]:
    return {i + 1: value for i, value in enumerate(powers)}


def tag_dict(report: TagReport) -> dict:
    """Preserve raw measurements and label user-defined RSSI estimates."""
    value = {
        "epc": report.epc.hex().upper() if report.epc is not None else None,
        "tid": report.tid.hex().upper() if report.tid is not None else None,
        "antenna": report.antenna,
        "antenna_mask": report.antenna_mask,
        "rssi_raw": report.rssi_raw,
        "rssi_dbm": report.rssi_dbm,
        "rssi_source": report.rssi_source,
        "rssi_in_calibration_range": report.rssi_in_calibration_range,
        "frequency_khz": report.frequency_khz,
        "phase_raw": report.phase_raw.hex().upper() if report.phase_raw is not None else None,
        "received_at": report.received_at,
        "timestamp_source": report.timestamp_source,
        "native": report,
    }
    if report.memory_data is not None:
        value["memory"] = report.memory_data.hex().upper()
        value["memory_bank"] = report.memory_bank
        value["word_address"] = report.word_address
    return value


def unsupported(operation: str):
    kind = CONTRACT.get(operation, Equivalence.UNSUPPORTED)
    if kind is Equivalence.UNVERIFIED:
        raise UnverifiedFeature(f"{operation}: no verified NATION-to-ZK mapping")
    raise UnsupportedFeature(f"{operation}: not available in the adapter contract")
