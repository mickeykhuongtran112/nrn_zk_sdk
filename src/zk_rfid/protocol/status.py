"""Status semantics are command-specific; a continuation is not an error."""

from dataclasses import dataclass
from ..models import Outcome

STATUS_NAMES = {
    0x00: "success",
    0x01: "inventory_complete",
    0x02: "inventory_timeout",
    0x03: "more_frames",
    0x04: "buffer_full",
    0x05: "access_password_error",
    0x09: "kill_failed",
    0x0A: "zero_kill_password",
    0x0B: "tag_command_unsupported",
    0x0C: "zero_access_password",
    0x0D: "read_protection_failed",
    0x0E: "unlock_failed",
    0x13: "persistence_failed",
    0x14: "power_adjustment_failed",
    0x26: "statistics",
    0x28: "heartbeat",
    0xF8: "antenna_error",
    0xF9: "command_failed",
    0xFA: "tag_communication_error",
    0xFB: "no_tag",
    0xFC: "tag_error",
    0xFD: "invalid_length",
    0xFE: "invalid_command_or_crc",
    0xFF: "parameter_error",
}


@dataclass(frozen=True)
class StatusInfo:
    code: int
    name: str
    outcome: Outcome
    terminal: bool
    tag_error: int | None = None


def interpret_status(command: int, status: int, data: bytes = b"") -> StatusInfo:
    name = STATUS_NAMES.get(status, f"unknown_status_{status:02X}")
    if command in (0x01, 0x0F, 0x19, 0x1A, 0x72) and status in (1, 2, 3, 4, 0x26):
        return StatusInfo(
            status, name, Outcome.PARTIAL if status in (2, 4) else Outcome.SUCCESS, status != 3
        )
    if command == 0xEE and status in (0, 0x28):
        return StatusInfo(status, name, Outcome.SUCCESS, False)
    return StatusInfo(
        status,
        name,
        Outcome.SUCCESS if status == 0 else Outcome.PARTIAL if status == 0x13 else Outcome.FAILURE,
        True,
        data[0] if status == 0xFC and data else None,
    )
