"""Standalone async SDK for ZK Gen2 UHF RFID readers (Python >= 3.11).

This file is the canonical implementation: copy it into your application and
import ZKReader, SerialTransport, InventoryConfig, etc. from zk_rfid.
Only SerialTransport.open() needs the optional pyserial dependency.
CPython and Pyodide share the same injected AsyncTransport contract.

Sections below contain models, protocol, pure command builders/decoders,
transport, dispatcher, inventory sessions, ZKReader and the NATION API adapter.
Use ZKReader for device I/O; module-level command builders only return Request
values and never open a port or transmit bytes. Import has no device side effects.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import math
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from enum import Enum, IntEnum
from typing import Callable, Generic, Protocol, TypeVar, runtime_checkable

# ==============================================================================
# SDK identity and logging
# ==============================================================================

# Native asynchronous Python SDK for ZK Gen2 UHF readers.


__version__ = "0.2.0.dev1"
SDK_NAME = "ZK RFID SDK"
SDK_VERSION = __version__


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Opt-in SDK logger; import does not modify application logging."""
    logger = logging.getLogger("zk_rfid")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger


# ==============================================================================
# Errors and execution outcomes
# ==============================================================================

# SDK exceptions; errors retain the native response and uncertain outcome.


class ZKError(Exception):
    """Base SDK exception."""


class ValidationError(ZKError, ValueError):
    """Invalid input; no command was transmitted."""


class ProtocolError(ZKError):
    """Invalid or unsupported response layout."""


class UnsupportedFeature(ZKError):
    """Operation outside the reader/tag capability."""


class UnverifiedFeature(UnsupportedFeature):
    """Insufficient evidence to choose a wire format or conversion."""


class StateError(ZKError):
    """Operation conflicts with reader state."""


class TransportError(ZKError):
    """Connection failed; reader may already have changed."""


class ExchangeError(TransportError):
    """Incomplete exchange, retaining valid responses already received."""

    def __init__(self, message, *, frames=(), transmitted=False):
        super().__init__(message)
        self.frames = tuple(frames)
        self.transmitted = transmitted


class RequestTimeout(ExchangeError, TimeoutError):
    """Host monotonic deadline expired (not a device status)."""


class QueueOverflow(ProtocolError):
    """Consumer could not keep up; loss is never silently hidden."""


class DeviceError(ZKError):
    def __init__(self, command, status, data=b"", tag_error=None):
        self.command, self.status, self.data, self.tag_error = command, status, data, tag_error
        super().__init__(
            f"ZK command 0x{command:02X}: status 0x{status:02X}"
            + (f", tag error 0x{tag_error:02X}" if tag_error is not None else "")
        )


class OperationError(ZKError):
    """Raised by require_success(), retaining the complete CommandResult."""

    def __init__(self, result):
        self.result = result
        super().__init__(f"Operation {result.outcome.value}: {'; '.join(result.diagnostics)}")


# ==============================================================================
# Typed values and validation
# ==============================================================================

# Public typed values; words are 16 bits, tag data remains lossless bytes.


T = TypeVar("T")


def integer(value: int, minimum: int, maximum: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValidationError(f"{name} must be an integer in {minimum}..{maximum}")
    return int(value)


def boolean(value: bool, name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{name} must be bool")
    return value


def octets(value: bytes, name: str, minimum=0, maximum=251) -> bytes:
    if not isinstance(value, bytes) or not minimum <= len(value) <= maximum:
        raise ValidationError(f"{name} must be bytes, length {minimum}..{maximum}")
    return value


class MemoryBank(IntEnum):
    RESERVED = 0
    EPC = 1
    TID = 2
    USER = 3


class Outcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class Confirmation(str, Enum):
    NONE = "none"
    TRANSMITTED = "transmitted"
    ACKNOWLEDGED = "acknowledged"
    READ_BACK = "read_back_verified"


class ReaderState(str, Enum):
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    STARTING = "starting"
    INVENTORYING = "inventorying"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


class InventoryMode(str, Enum):
    ANSWER = "answer"
    SCENARIO = "scenario"
    REAL_TIME = "real_time"


class InventoryData(str, Enum):
    EPC = "epc"
    TID = "tid"
    FAST_ID = "fastid"
    MIX = "mix"


class WorkingMode(IntEnum):
    ANSWER = 0
    REAL_TIME = 1
    TRIGGER = 2


class LockTarget(IntEnum):
    KILL_PASSWORD = 0
    ACCESS_PASSWORD = 1
    EPC = 2
    TID = 3
    USER = 4


class LockProtection(IntEnum):
    UNLOCK = 0
    PERMANENT_UNLOCK = 1
    PASSWORD = 2
    PERMANENT_LOCK = 3


@dataclass(frozen=True)
class TagMask:
    bank: MemoryBank
    bit_address: int
    bit_length: int
    data: bytes

    def __post_init__(self):
        integer(self.bank, 1, 3, "mask bank")
        integer(self.bit_address, 0, 16383, "mask bit_address")
        integer(self.bit_length, 0, 255, "mask bit_length")
        octets(self.data, "mask data", (self.bit_length + 7) // 8, (self.bit_length + 7) // 8)
        if self.bit_address + self.bit_length > 16384:
            raise ValidationError("Mask extends beyond bit address 16383")
        padding = (-self.bit_length) % 8
        if padding and self.data[-1] & ((1 << padding) - 1):
            raise ValidationError("Unused low mask bits must be zero")

    def encode(self) -> bytes:
        return (
            bytes((self.bank,))
            + self.bit_address.to_bytes(2, "big")
            + bytes((self.bit_length,))
            + self.data
        )


@dataclass(frozen=True)
class TagTarget:
    """Exactly one full EPC or nonempty mask. None in an API means unfiltered."""

    epc: bytes | None = None
    mask: TagMask | None = None

    def __post_init__(self):
        if (self.epc is None) == (self.mask is None):
            raise ValidationError("Provide exactly one of epc or mask")
        if self.epc is not None:
            octets(self.epc, "target EPC", 2, 30)
            if len(self.epc) % 2:
                raise ValidationError("EPC must contain whole words")
        elif not isinstance(self.mask, TagMask) or not self.mask.bit_length:
            raise ValidationError("Target mask must be a nonempty TagMask")


@dataclass(frozen=True)
class CommandResult(Generic[T]):
    outcome: Outcome
    data: T | None = None
    command: int | None = None
    status: int | None = None
    tag_error: int | None = None
    raw_data: bytes = b""
    confirmation: Confirmation = Confirmation.NONE
    diagnostics: tuple[str, ...] = ()
    steps: tuple["CommandResult", ...] = ()
    evidence: str = "documented; hardware unverified"

    @property
    def ok(self) -> bool:
        return self.outcome is Outcome.SUCCESS

    def require_success(self) -> T:
        if not self.ok:
            raise OperationError(self)
        return self.data


@dataclass(frozen=True)
class ReaderInfo:
    address: int
    firmware: tuple[int, int]
    model_code: int
    protocol_flags: int
    max_frequency_raw: int
    min_frequency_raw: int
    power_dbm: int
    scan_time_100ms: int
    antenna_raw: int
    reserved: bytes
    antenna_check: bool


@dataclass(frozen=True)
class InventoryConfig:
    data: InventoryData = InventoryData.EPC
    q: int = 4
    session: int = 0
    target: int = 0
    antenna: int = 1
    scan_time_100ms: int = 20
    mask: TagMask | None = None
    tid_word_address: int = 0
    tid_word_count: int = 6
    phase: bool = False
    statistics: bool = False
    special_strategy: bool = False
    memory_bank: MemoryBank = MemoryBank.USER
    word_address: int = 0
    word_count: int = 1
    access_password: bytes = b"\0" * 4


@dataclass(frozen=True)
class TagReport:
    epc: bytes | None = None
    tid: bytes | None = None
    memory_data: bytes | None = None
    memory_bank: MemoryBank | None = None
    word_address: int | None = None
    antenna: int | None = None
    antenna_raw: int | None = None
    antenna_mask: int | None = None
    rssi_raw: int | None = None
    rssi_dbm: float | None = None
    phase_raw: bytes | None = None
    phase_begin_raw: int | None = None
    phase_end_raw: int | None = None
    phase_radians: float | None = None
    frequency_khz: int | None = None
    received_at: float | None = None
    timestamp_source: str = "host_monotonic"
    read_count: int | None = None
    raw: bytes = b""

    # Ex10 V6.8 demo convention; preserve both words and the original bytes.
    # The legacy singular phase_radians stays None: a report has two phases.
    phase_begin_degrees: float | None = None
    phase_end_degrees: float | None = None
    phase_begin_radians: float | None = None
    phase_end_radians: float | None = None
    phase_conversion: str | None = None
    rssi_source: str | None = None
    rssi_in_calibration_range: bool | None = None


@dataclass(frozen=True)
class InventoryStatistics:
    antenna_raw: int
    reads_per_second: int
    total_reads: int


@dataclass(frozen=True)
class Heartbeat:
    packet_number: int
    antenna_status: tuple[int, ...]
    total_reads: int


@dataclass(frozen=True)
class InventoryOutcome:
    reports: tuple[TagReport, ...] = ()
    termination_reason: str = "completed"
    outcome: Outcome = Outcome.SUCCESS
    status: int | None = None
    complete: bool = True
    statistics: InventoryStatistics | None = None
    diagnostics: tuple[str, ...] = ()
    received_count: int = 0
    dropped_count: int = 0

    @property
    def unique_count(self) -> int:
        return len({(r.epc, r.tid) for r in self.reports if r.epc is not None or r.tid is not None})


@dataclass(frozen=True)
class Region:
    band: int
    min_channel: int
    max_channel: int


@dataclass(frozen=True)
class GPIOState:
    input1: bool
    output1: bool
    output2: bool
    raw: int


@dataclass(frozen=True)
class RealTimeConfig:
    pause_ms: int = 50
    filter_seconds: int = 0
    q: int = 4
    session: int = 0
    special_strategy: bool = False
    mask: TagMask | None = None
    tid_word_address: int = 0
    tid_word_count: int = 0


@dataclass(frozen=True)
class WorkingModeConfig:
    mode: WorkingMode
    config: RealTimeConfig


@dataclass(frozen=True)
class BufferCounts:
    stored_tags: int
    round_reads: int


@dataclass(frozen=True)
class WritePower:
    enabled: bool
    power_dbm: int


@dataclass(frozen=True)
class QueryParameters:
    q: int
    session: int
    phase: bool = False


@dataclass(frozen=True)
class ScanParameters:
    interval_10ms: int
    dwell_100ms: int
    count: int


@dataclass(frozen=True)
class TIDParameters:
    word_address: int
    word_count: int


@dataclass
class ParserDiagnostics:
    frames: int = 0
    discarded_bytes: int = 0
    crc_failures: int = 0
    buffer_overflows: int = 0
    unexpected_frames: int = 0


# ==============================================================================
# Reader capabilities
# ==============================================================================

# Declared wire capabilities are not inferred hardware verification.


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


# ==============================================================================
# RSSI calibration and phase units
# ==============================================================================

# Vendor phase convention and explicitly user-defined RSSI mapping.


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


# ==============================================================================
# Structured trace events
# ==============================================================================

# Optional observational trace, independent of transport and application UI.


@dataclass(frozen=True)
class TraceEvent:
    """Host monotonic timestamp; raw bytes are wire bytes, never inferred RF timing."""

    sequence: int
    timestamp: float
    kind: str
    exchange_id: int | None = None
    command: int | None = None
    address: int | None = None
    status: int | None = None
    raw: bytes = b""
    detail: str = ""


class TraceEmitter:
    """A synchronous observer must return promptly; observer errors never affect RF I/O."""

    def __init__(self, observer: Callable[[TraceEvent], None] | None = None):
        self.observer = observer
        self.sequence = 0
        self.observer_errors = 0
        self.logger = logging.getLogger("zk_rfid.trace")

    def emit(self, kind: str, **fields) -> TraceEvent:
        self.sequence += 1
        event = TraceEvent(self.sequence, time.monotonic(), kind, **fields)
        self.logger.debug(
            "%s exchange=%s cmd=%s status=%s %s %s",
            kind,
            event.exchange_id,
            event.command,
            event.status,
            event.raw.hex(),
            event.detail,
        )
        if self.observer is not None:
            try:
                self.observer(event)
            except Exception:
                self.observer_errors += 1
                self.logger.debug("Trace observer raised; ignored to preserve I/O", exc_info=True)
        return event


# ==============================================================================
# Native RF profile catalogue
# ==============================================================================

# Native Ex10 RF profiles transcribed from V2.25 pp.85-86.
#
# These are documented physical parameters, not RF equivalence with NATION.
# No profile is selected automatically and availability is firmware-dependent.


@dataclass(frozen=True)
class RFProfile:
    id: int
    modulation: str
    pie: float
    tari_us: float
    blf_khz: int
    encoding: str
    evidence: str = "V2.25 pp.85-86; hardware unverified"


PROFILES = {
    1: RFProfile(1, "PR_ASK", 2.0, 7.5, 640, "Miller2"),
    3: RFProfile(3, "PR_ASK", 2.0, 20.0, 320, "Miller2"),
    5: RFProfile(5, "PR_ASK", 2.0, 20.0, 320, "Miller4"),
    7: RFProfile(7, "PR_ASK", 2.0, 20.0, 250, "Miller4"),
    11: RFProfile(11, "PR_ASK", 2.0, 7.5, 640, "FM0"),
    12: RFProfile(12, "PR_ASK", 2.0, 15.0, 320, "Miller2"),
    13: RFProfile(13, "PR_ASK", 2.0, 20.0, 160, "Miller8"),
    15: RFProfile(15, "PR_ASK", 2.0, 7.5, 640, "Miller4"),
    102: RFProfile(102, "PR_ASK", 2.0, 7.5, 640, "FM0"),
    103: RFProfile(103, "DSB", 1.5, 6.25, 640, "FM0"),
    104: RFProfile(104, "DSB", 1.5, 6.25, 320, "FM0"),
    120: RFProfile(120, "DSB", 1.5, 6.25, 640, "Miller2"),
    123: RFProfile(123, "PR_ASK", 2.0, 20.0, 320, "Miller2"),
    124: RFProfile(124, "PR_ASK", 2.0, 7.5, 640, "Miller2"),
    125: RFProfile(125, "PR_ASK", 2.0, 15.0, 320, "Miller2"),
    126: RFProfile(126, "PR_ASK", 1.5, 12.5, 320, "Miller2"),
    141: RFProfile(141, "PR_ASK", 2.0, 20.0, 320, "Miller4"),
    146: RFProfile(146, "PR_ASK", 2.0, 20.0, 250, "Miller4"),
    147: RFProfile(147, "PR_ASK", 2.0, 7.5, 640, "Miller4"),
    148: RFProfile(148, "PR_ASK", 1.5, 7.5, 640, "Miller4"),
    185: RFProfile(185, "PR_ASK", 2.0, 20.0, 160, "Miller8"),
    202: RFProfile(202, "PR_ASK", 2.0, 15.0, 426, "FM0"),
    203: RFProfile(203, "PR_ASK", 1.5, 12.5, 426, "FM0"),
    205: RFProfile(205, "PR_ASK", 2.0, 20.0, 50, "FM0"),
    222: RFProfile(222, "PR_ASK", 2.0, 20.0, 320, "Miller2"),
    223: RFProfile(223, "PR_ASK", 2.0, 15.0, 320, "Miller2"),
    224: RFProfile(224, "PR_ASK", 1.5, 12.5, 320, "Miller2"),
    225: RFProfile(225, "PR_ASK", 2.0, 15.0, 426, "Miller2"),
    226: RFProfile(226, "PR_ASK", 1.5, 12.5, 426, "Miller2"),
    241: RFProfile(241, "PR_ASK", 2.0, 20.0, 320, "Miller4"),
    244: RFProfile(244, "PR_ASK", 2.0, 20.0, 250, "Miller4"),
    285: RFProfile(285, "PR_ASK", 2.0, 20.0, 160, "Miller8"),
    302: RFProfile(302, "PR_ASK", 2.0, 7.5, 640, "FM0"),
    323: RFProfile(323, "PR_ASK", 2.0, 7.5, 640, "Miller2"),
    324: RFProfile(324, "PR_ASK", 2.0, 20.0, 320, "Miller2"),
    325: RFProfile(325, "PR_ASK", 2.0, 15.0, 320, "Miller2"),
    326: RFProfile(326, "PR_ASK", 1.5, 12.5, 320, "Miller2"),
    342: RFProfile(342, "PR_ASK", 2.0, 20.0, 320, "Miller4"),
    343: RFProfile(343, "PR_ASK", 2.0, 20.0, 250, "Miller4"),
    344: RFProfile(344, "PR_ASK", 2.0, 7.5, 640, "Miller4"),
    345: RFProfile(345, "PR_ASK", 1.5, 7.5, 640, "Miller4"),
    382: RFProfile(382, "PR_ASK", 2.0, 20.0, 160, "Miller8"),
    4123: RFProfile(4123, "PR_ASK", 2.0, 20.0, 320, "PSK2"),
    4124: RFProfile(4124, "PR_ASK", 2.0, 7.5, 640, "BPSK2"),
    4141: RFProfile(4141, "PR_ASK", 2.0, 20.0, 320, "BPSK4"),
    4146: RFProfile(4146, "PR_ASK", 2.0, 20.0, 250, "BPSK4"),
    4148: RFProfile(4148, "PR_ASK", 1.5, 7.5, 640, "BPSK4"),
    4185: RFProfile(4185, "PR_ASK", 2.0, 20.0, 160, "BPSK8"),
    5123: RFProfile(5123, "PR_ASK", 2.0, 20.0, 320, "M+B2"),
    5124: RFProfile(5124, "PR_ASK", 2.0, 7.5, 640, "M+B2"),
    5141: RFProfile(5141, "PR_ASK", 2.0, 20.0, 320, "M+B4"),
    5146: RFProfile(5146, "PR_ASK", 2.0, 20.0, 250, "M+B4"),
    5148: RFProfile(5148, "PR_ASK", 1.5, 7.5, 640, "M+B4"),
    5185: RFProfile(5185, "PR_ASK", 2.0, 20.0, 160, "M+B8"),
}


def get_profile_definition(profile_id: int) -> RFProfile:
    try:
        return PROFILES[profile_id]
    except KeyError as error:
        raise UnverifiedFeature(
            f"No physical definition for native profile {profile_id}"
        ) from error


# ==============================================================================
# Protocol: opcodes and constants
# ==============================================================================

# V2.25 Gen2/reader namespace: 0x50/51 mean Ex10 fast inventory, never 6B.


CRC16_INIT = 0xFFFF
CRC16_POLY = 0x8408
MAX_COMMAND_DATA = 251
MAX_RESPONSE_DATA = 250
BROADCAST_ADDRESS = 0xFF


class Command(IntEnum):
    INVENTORY = 0x01
    READ_MEMORY = 0x02
    WRITE_MEMORY = 0x03
    WRITE_EPC = 0x04
    KILL = 0x05
    LOCK = 0x06
    BLOCK_ERASE = 0x07
    SINGLE_INVENTORY = 0x0F
    BLOCK_WRITE = 0x10
    READ_MEMORY_EXTENDED = 0x15
    WRITE_MEMORY_EXTENDED = 0x16
    BUFFER_INVENTORY = 0x18
    MIX_INVENTORY = 0x19
    INVENTORY_EPC = 0x1A
    READER_INFO = 0x21
    SET_REGION = 0x22
    SET_ADDRESS = 0x24
    SET_SCAN_TIME = 0x25
    SET_BAUDRATE = 0x28
    SET_POWER = 0x2F
    INDICATOR = 0x33
    SET_ANTENNAS = 0x3F
    SET_BUZZER = 0x40
    SET_GPIO = 0x46
    GET_GPIO = 0x47
    SERIAL_NUMBER = 0x4C
    FAST_START = 0x50
    FAST_STOP = 0x51
    SET_ANTENNA_CHECK = 0x66
    SET_INTERFACE = 0x6A
    RETURN_LOSS_THRESHOLD = 0x6E
    SET_BUFFER_LENGTH = 0x70
    GET_BUFFER_LENGTH = 0x71
    READ_BUFFER = 0x72
    CLEAR_BUFFER = 0x73
    BUFFER_COUNT = 0x74
    SET_REAL_TIME = 0x75
    SET_WORKING_MODE = 0x76
    GET_WORKING_MODE = 0x77
    HEARTBEAT = 0x78
    SET_WRITE_POWER = 0x79
    GET_WRITE_POWER = 0x7A
    WRITE_RETRIES = 0x7B
    PROFILE = 0x7F
    DRM = 0x90
    RETURN_LOSS = 0x91
    TEMPERATURE = 0x92
    STOP_INVENTORY = 0x93
    GET_POWER = 0x94
    SELECT = 0x9A
    GET_REGION = 0x9E
    SET_CONFIG = 0xEA
    GET_CONFIG = 0xEB
    TAG_REPORT = 0xEE


class ConfigID(IntEnum):
    SCAN = 7
    TAG_FOCUS = 8
    QUERY = 9
    TID = 10
    MASK = 11
    IMPINJ_SCAN = 25
    IMPINJ_SCAN_ID = 29
    CUSTOM_PROFILES = 31


# ==============================================================================
# Protocol: CRC
# ==============================================================================

# UART CRC: reflected 0x8408, init FFFF, no xorout, low byte first.


def crc16(data: bytes, initial: int = CRC16_INIT) -> int:
    crc = initial
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (CRC16_POLY if crc & 1 else 0)
    return crc & 0xFFFF


def append_crc(data: bytes) -> bytes:
    return data + crc16(data).to_bytes(2, "little")


# ==============================================================================
# Protocol: command and response frames
# ==============================================================================

# Lossless framing. Len counts everything after itself.


@dataclass(frozen=True)
class ResponseFrame:
    address: int
    command: int
    status: int
    data: bytes
    raw: bytes


def encode_command(address: int, command: int, data: bytes = b"") -> bytes:
    integer(address, 0, 255, "address")
    integer(command, 0, 255, "command")
    octets(data, "command data")
    return append_crc(bytes((len(data) + 4, address, command)) + data)


def decode_response(raw: bytes) -> ResponseFrame:
    if not 6 <= len(raw) <= 256 or raw[0] != len(raw) - 1:
        raise ProtocolError("Response length mismatch")
    if crc16(raw) != 0:
        raise ProtocolError("Response CRC mismatch")
    return ResponseFrame(raw[1], raw[2], raw[3], raw[4:-2], bytes(raw))


# ==============================================================================
# Protocol: incremental stream parser
# ==============================================================================

# Bounded incremental parser with CRC resynchronization and loss counters.


class FrameParser:
    def __init__(self, max_buffer: int = 4096):
        self.max_buffer = integer(max_buffer, 256, 1048576, "max_buffer")
        self.buffer = bytearray()
        self.diagnostics = ParserDiagnostics()

    def reset(self):
        self.buffer.clear()

    def feed(self, data: bytes) -> list[ResponseFrame]:
        result = []
        for offset in range(0, len(data), 256):
            self.buffer.extend(data[offset : offset + 256])
            while self.buffer:
                if self.buffer[0] < 5:
                    self._discard(1)
                    continue
                length = self.buffer[0] + 1
                if len(self.buffer) >= length:
                    raw = bytes(self.buffer[:length])
                    if crc16(raw) == 0:
                        result.append(decode_response(raw))
                        del self.buffer[:length]
                        self.diagnostics.frames += 1
                        continue
                    self.diagnostics.crc_failures += 1
                    self._discard(1)
                    continue
                found = None
                for pos in range(1, len(self.buffer) - 5):
                    end = pos + self.buffer[pos] + 1
                    if self.buffer[pos] >= 5 and end <= len(self.buffer):
                        if crc16(self.buffer[pos:end]) == 0:
                            found = pos
                            break
                if found is not None:
                    self._discard(found)
                    continue
                break
            if len(self.buffer) > self.max_buffer:
                self.diagnostics.buffer_overflows += 1
                self._discard(len(self.buffer) - 255)
        return result

    def _discard(self, count):
        self.diagnostics.discarded_bytes += count
        del self.buffer[:count]


# ==============================================================================
# Protocol: native status interpretation
# ==============================================================================

# Status semantics are command-specific; a continuation is not an error.


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


# ==============================================================================
# Transport: async byte interface
# ==============================================================================

# Injected nonblocking byte transport. Empty read means EOF, not polling timeout.


@runtime_checkable
class AsyncTransport(Protocol):
    async def open(self) -> None: ...
    async def close(self) -> None: ...
    async def read(self, size: int = 4096) -> bytes: ...
    async def write(self, data: bytes) -> int:
        """Return accepted count; short writes are supported, zero is an error."""
        ...


# ==============================================================================
# Transport: optional CPython serial
# ==============================================================================

# Optional CPython transport; pyserial is imported only by open().


class SerialTransport:
    def __init__(self, port: str, baudrate=57600, *, read_timeout=0.05, write_timeout=1.0):
        if not isinstance(port, str) or not port:
            raise ValueError("Explicit serial port is required")
        self.port = port
        self.baudrate = integer(baudrate, 1, 4000000, "baudrate")
        if not 0 < read_timeout <= 1 or not 0 < write_timeout <= 30:
            raise ValueError("Invalid serial timeout")
        self.read_timeout, self.write_timeout = read_timeout, write_timeout
        self._serial = None

    async def open(self):
        if self._serial is not None:
            return
        try:
            import serial
        except ImportError as error:
            raise TransportError(
                "Install pyserial on CPython: python -m pip install pyserial"
            ) from error

        def create():
            return serial.Serial(
                self.port,
                self.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=self.read_timeout,
                write_timeout=self.write_timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )

        task = asyncio.create_task(asyncio.to_thread(create))
        try:
            self._serial = await asyncio.shield(task)
        except asyncio.CancelledError:
            # Do not leak a serial handle opened by a still-running worker.
            opened = await task
            await asyncio.to_thread(opened.close)
            raise
        except Exception as error:
            raise TransportError(f"Cannot open {self.port}: {error}") from error

    async def read(self, size=4096) -> bytes:
        while self._serial is not None:
            port = self._serial
            try:
                data = await asyncio.to_thread(port.read, min(size, max(1, port.in_waiting)))
            except Exception as error:
                if self._serial is None:
                    return b""
                raise TransportError(f"Serial read failed: {error}") from error
            if data:
                return data
            # A serial timeout is not EOF; loop has awaited the worker.
        return b""

    async def write(self, data: bytes) -> int:
        if self._serial is None:
            raise TransportError("Serial port is closed")
        try:
            return await asyncio.to_thread(self._serial.write, data)
        except Exception as error:
            raise TransportError(f"Serial write failed: {error}") from error

    async def set_baudrate(self, baudrate: int):
        if self._serial is None:
            raise TransportError("Serial port is closed")
        await asyncio.to_thread(setattr, self._serial, "baudrate", baudrate)
        self.baudrate = baudrate

    async def close(self):
        port, self._serial = self._serial, None
        if port is not None:

            def close_port():
                if hasattr(port, "cancel_read"):
                    port.cancel_read()
                if hasattr(port, "cancel_write"):
                    port.cancel_write()
                port.close()

            await asyncio.to_thread(close_port)


# ==============================================================================
# Commands: request values and response validators
# ==============================================================================

# Small command value and strict response helpers, no I/O.


def raw(data: bytes) -> bytes:
    return data


def exact(data: bytes, size: int) -> bytes:
    if len(data) != size:
        raise ProtocolError(f"Expected {size} response bytes, received {len(data)}")
    return data


def ack(data: bytes) -> None:
    exact(data, 0)


def u8(data: bytes) -> int:
    return exact(data, 1)[0]


def u16(data: bytes) -> int:
    return int.from_bytes(exact(data, 2), "big")


def switch(data: bytes) -> bool:
    value = u8(data)
    if value not in (0, 1):
        raise ProtocolError("Invalid boolean response")
    return bool(value)


@dataclass(frozen=True)
class Request(Generic[T]):
    command: int
    data: bytes = b""
    decode: Callable[[bytes], T] = raw
    mutating: bool = False

    def __post_init__(self):
        octets(self.data, "command payload")


# ==============================================================================
# Commands: reader information
# ==============================================================================

# V2.25 sections 8.4.1, 8.4.12 (table layout, not erroneous example Len).


def decode_reader_info(data: bytes, address: int = 0) -> ReaderInfo:
    exact(data, 12)
    if data[11] not in (0, 1):
        raise ProtocolError("Invalid antenna-check field in reader information")
    return ReaderInfo(
        address,
        tuple(data[:2]),
        data[2],
        data[3],
        data[4],
        data[5],
        data[6],
        data[7],
        data[8],
        data[9:11],
        bool(data[11]),
    )


def get_reader_info() -> Request[ReaderInfo]:
    return Request(0x21, decode=decode_reader_info)


def get_serial_number() -> Request[bytes]:
    return Request(0x4C, decode=lambda d: exact(d, 4))


# ==============================================================================
# Commands: reader configuration and real-time mode
# ==============================================================================

# Reader control and real-time mode, V2.25 sections 8.4.3-5/15/22-25.


BAUD_CODES = {9600: 0, 19200: 1, 38400: 2, 57600: 5, 115200: 6}
PAUSE_CODES = {10: 0, 20: 1, 30: 2, 50: 3, 100: 4}


def set_address(address: int) -> Request[None]:
    return Request(0x24, bytes((integer(address, 0, 254, "address"),)), ack, True)


def set_scan_time(scan_time_100ms: int) -> Request[None]:
    integer(scan_time_100ms, 0, 255, "scan_time_100ms")
    if scan_time_100ms in (1, 2):
        raise ValidationError("Scan time must be 0 (unlimited) or 3..255")
    return Request(0x25, bytes((scan_time_100ms,)), ack, True)


def set_baudrate(baudrate: int) -> Request[None]:
    integer(baudrate, 9600, 115200, "baudrate")
    if baudrate not in BAUD_CODES:
        raise ValidationError(f"Supported baud rates: {tuple(BAUD_CODES)}")
    return Request(0x28, bytes((BAUD_CODES[baudrate],)), ack, True)


def set_interface(interface: str) -> Request[None]:
    if interface not in ("usb", "uart"):
        raise ValidationError("interface must be usb or uart (effective after power cycle)")
    return Request(0x6A, bytes((0 if interface == "usb" else 1,)), ack, True)


def set_working_mode(mode: WorkingMode) -> Request[None]:
    return Request(0x76, bytes((integer(mode, 0, 2, "mode"),)), ack, True)


def encode_real_time(config: RealTimeConfig) -> bytes:
    if config.pause_ms not in PAUSE_CODES:
        raise ValidationError("pause_ms must be 10, 20, 30, 50 or 100")
    integer(config.filter_seconds, 0, 255, "filter_seconds")
    integer(config.q, 0, 15, "q")
    integer(config.session, 0, 255, "session")
    if config.session not in (0, 1, 2, 3, 255):
        raise ValidationError("Real-time session must be 0..3 or 255")
    q = config.q | (64 if boolean(config.special_strategy, "special_strategy") else 0)
    integer(config.tid_word_address, 0, 255, "tid_word_address")
    integer(config.tid_word_count, 0, 15, "tid_word_count")
    mask = b"" if config.mask is None else config.mask.encode()
    tid = bytes((config.tid_word_address, config.tid_word_count)) if config.tid_word_count else b""
    if config.tid_word_count and config.session == 255:
        raise ValidationError("Auto session is documented only for EPC")
    return (
        bytes((0, PAUSE_CODES[config.pause_ms], config.filter_seconds, q, config.session))
        + mask
        + tid
    )


def set_real_time(config: RealTimeConfig) -> Request[None]:
    return Request(0x75, encode_real_time(config), ack, True)


def decode_working_mode(data: bytes) -> WorkingModeConfig:
    exact(data, 44)  # Fixed 32-byte mask storage in Get response, not variable Set layout.
    if data[0] > 2 or data[1] != 0 or data[2] > 4 or data[4] & ~0x4F:
        raise ProtocolError("Unsupported working mode/protocol/query response")
    bits = data[9]
    mask_data = data[10 : 10 + (bits + 7) // 8]
    if any(data[10 + (bits + 7) // 8 : 42]):
        raise ProtocolError("Nonzero unused real-time mask bytes")
    try:
        mask = TagMask(data[6], int.from_bytes(data[7:9], "big"), bits, mask_data) if bits else None
        cfg = RealTimeConfig(
            tuple(PAUSE_CODES)[data[2]],
            data[3],
            data[4] & 15,
            data[5],
            bool(data[4] & 64),
            mask,
            data[42],
            data[43],
        )
        encode_real_time(cfg)
    except ValidationError as error:
        raise ProtocolError(str(error)) from error
    return WorkingModeConfig(WorkingMode(data[0]), cfg)


def get_working_mode() -> Request[WorkingModeConfig]:
    return Request(0x77, decode=decode_working_mode)


def heartbeat(interval_30s: int | None = None) -> Request[int]:
    value = 0 if interval_30s is None else 128 | integer(interval_30s, 0, 127, "interval_30s")

    def decode(data):
        n = exact(data, 1)[0]
        if n > 127:
            raise ProtocolError("Invalid heartbeat interval")
        return n

    return Request(0x78, bytes((value,)), decode, interval_30s is not None)


# ==============================================================================
# Commands: RF power
# ==============================================================================

# RF power is integer dBm; write-power bit7 is enable, not persistence.


def set_power(power_dbm: int | tuple[int, ...], *, ports: int, persist=False) -> Request[None]:
    boolean(persist, "persist")
    powers = (power_dbm,) if isinstance(power_dbm, int) else tuple(power_dbm)
    if len(powers) not in (1, ports):
        raise ValidationError("Supply one global value or exactly one per configured antenna")
    values = bytes(integer(p, 0, 30, "power_dbm") | (0 if persist else 128) for p in powers)
    return Request(0x2F, values, ack, True)


def get_power(*, ports: int) -> Request[tuple[int, ...]]:
    def decode(data):
        exact(data, ports)
        if any(p > 30 for p in data):
            raise ProtocolError("Power response is outside documented 0..30 dBm")
        return tuple(data)

    return Request(0x94, decode=decode)


def set_write_power(power_dbm: int | None) -> Request[None]:
    value = 0 if power_dbm is None else 128 | integer(power_dbm, 0, 30, "power_dbm")
    return Request(0x79, bytes((value,)), ack, True)


def decode_write_power(data: bytes) -> WritePower:
    value = exact(data, 1)[0]
    if value & 127 > 30:
        raise ProtocolError("Invalid write power")
    return WritePower(bool(value & 128), value & 127)


def get_write_power() -> Request[WritePower]:
    return Request(0x7A, decode=decode_write_power)


def write_retries(count: int | None = None) -> Request[int]:
    value = 0 if count is None else 128 | integer(count, 0, 7, "write retries")

    def decode(data):
        n = exact(data, 1)[0]
        if n > 7:
            raise ProtocolError("Invalid write retries")
        return n

    return Request(0x7B, bytes((value,)), decode, count is not None)


# ==============================================================================
# Commands: antenna selection and detection
# ==============================================================================

# Antenna layouts differ for 1/4, 8 and 16 ports.


def set_antennas(mask: int, *, ports: int, persist=False) -> Request[None]:
    integer(mask, 1, (1 << ports) - 1, "antenna mask")
    boolean(persist, "persist")
    data = (
        bytes((mask | (0 if persist else 128),))
        if ports <= 4
        else bytes((0 if persist else 1,)) + mask.to_bytes(2, "big")
    )
    return Request(0x3F, data, ack, True)


def set_antenna_check(enabled: bool) -> Request[None]:
    return Request(0x66, bytes((boolean(enabled, "enabled"),)), ack, True)


def decode_antenna(raw: int, *, ports: int, mask_encoding=False) -> dict:
    if ports == 16 and not mask_encoding:
        if raw >= 16:
            raise ProtocolError("Invalid 16-port antenna index")
        return dict(antenna=raw + 1, antenna_raw=raw, antenna_mask=1 << raw)
    if raw <= 0 or raw >> ports:
        raise ProtocolError("Invalid antenna mask")
    return dict(
        antenna=raw.bit_length() if raw & (raw - 1) == 0 else None,
        antenna_raw=raw,
        antenna_mask=raw,
    )


# ==============================================================================
# Commands: region, channels and RF profiles
# ==============================================================================

# Native frequency tables and profile IDs. No cross-vendor numeric mapping.


# Band -> base kHz, spacing kHz, max index, per V2.25 pp.61-62.
REGIONS = {
    0: (840000, 2000, 60),
    1: (920125, 250, 19),
    2: (902750, 500, 49),
    3: (917100, 200, 31),
    4: (865100, 200, 14),
    6: (868000, 100, 6),
    8: (840125, 250, 19),
    9: (865700, 600, 3),
    12: (902000, 500, 52),
    16: (920250, 500, 9),
    17: (920750, 500, 13),
    18: (916300, 1200, 2),
    19: (919250, 500, 7),
    22: (920250, 500, 9),
    23: (920250, 500, 9),
    24: (920250, 500, 9),
    25: (865100, 600, 3),
    26: (916250, 500, 22),
    27: (918750, 500, 7),
    28: (916250, 500, 0),
    30: (922250, 500, 9),
    31: (916800, 1200, 3),
    32: (916250, 500, 22),
    33: (916200, 1200, 3),
    34: (915600, 200, 16),
    35: (918250, 500, 3),
}
# Discontinuous band formulas (21,29) have ambiguous second-segment indexing.
BAND_MAX = {**{k: v[2] for k, v in REGIONS.items()}, 21: 34, 29: 3}


def validate_region(region: Region) -> Region:
    integer(region.band, 0, 35, "band")
    if region.band not in BAND_MAX:
        raise ValidationError("Reserved or undocumented band")
    integer(region.min_channel, 0, BAND_MAX[region.band], "min_channel")
    integer(region.max_channel, region.min_channel, BAND_MAX[region.band], "max_channel")
    return region


def channel_frequency_khz(band: int, channel: int) -> int:
    validate_region(Region(band, channel, channel))
    if band not in REGIONS:
        raise UnverifiedFeature("Discontinuous region formula requires firmware confirmation")
    base, step, _ = REGIONS[band]
    return base + channel * step


def set_region(region: Region, *, persist=False, legacy=False) -> Request[None]:
    validate_region(region)
    boolean(persist, "persist")
    boolean(legacy, "legacy")
    if legacy:
        if region.band > 15 or not persist:
            raise ValidationError("Legacy region requires band <=15 and persistent setting")
        data = bytes(
            (
                ((region.band >> 2) << 6) | region.max_channel,
                ((region.band & 3) << 6) | region.min_channel,
            )
        )
    else:
        data = bytes((0 if persist else 1, region.band, region.max_channel, region.min_channel))
    return Request(0x22, data, ack, True)


def decode_region(data: bytes) -> Region:
    exact(data, 3)
    try:
        return validate_region(Region(data[0], data[2], data[1]))
    except ValidationError as error:
        raise ProtocolError(str(error)) from error


def get_region() -> Request[Region]:
    return Request(0x9E, decode=decode_region)


def profile(profile_id: int | None = None, *, persist=False, extended=True) -> Request[int]:
    boolean(persist, "persist")
    boolean(extended, "extended")
    if profile_id is not None:
        integer(profile_id, 0, 65535 if extended else 63, "profile_id")
    if extended:
        data = bytes((0 if profile_id is None else 1 if persist else 2,))
        data += (profile_id or 0).to_bytes(2, "big")
    else:
        data = bytes((0 if profile_id is None else 128 | (0 if persist else 64) | profile_id,))
    return Request(0x7F, data, u16 if extended else u8, profile_id is not None)


def drm(enabled: bool | None = None) -> Request[bool]:
    value = 0 if enabled is None else 128 | boolean(enabled, "enabled")
    return Request(0x90, bytes((value,)), switch, enabled is not None)


# ==============================================================================
# Commands: Ex10 configuration
# ==============================================================================

# Typed Ex10 CFG7/8/9/10/11/25/29/31; conflicting lengths are explicit.


SCENARIO_SESSIONS = (0, 1, 2, 3, 128, 252, 253, 254, 255)


def encode_scan(value: ScanParameters) -> bytes:
    integer(value.interval_10ms, 0, 6, "interval_10ms")
    integer(value.dwell_100ms, 0, 255, "dwell_100ms")
    if value.dwell_100ms == 1:
        raise ValidationError("Dwell accepts 0 (documented default) or 2..255")
    return bytes((value.interval_10ms, value.dwell_100ms, integer(value.count, 0, 5, "count")))


def encode_query(value: QueryParameters) -> bytes:
    integer(value.q, 0, 15, "q")
    integer(value.session, 0, 255, "session")
    if value.session not in SCENARIO_SESSIONS:
        raise ValidationError("Unsupported Scenario session")
    return bytes((value.q | (16 if boolean(value.phase, "phase") else 0), value.session))


def encode_tid(value: TIDParameters) -> bytes:
    return bytes(
        (
            integer(value.word_address, 0, 255, "TID word_address"),
            integer(value.word_count, 0, 15, "TID word_count"),
        )
    )


def encode_profiles(profiles: tuple[int, int, int]) -> bytes:
    if len(profiles) != 3:
        raise ValidationError("CFG31 requires exactly three native profile IDs")
    return b"".join(integer(v, 0, 65535, "profile_id").to_bytes(2, "big") for v in profiles)


def decode_mask(data: bytes) -> TagMask:
    if len(data) < 4:
        raise ProtocolError("Truncated CFG11 mask")
    try:
        return TagMask(data[0], int.from_bytes(data[1:3], "big"), data[3], data[4:])
    except ValidationError as error:
        raise ProtocolError(str(error)) from error


def decode_config(number: int, data: bytes):
    try:
        if number == 7:
            value = ScanParameters(*exact(data, 3))
            encode_scan(value)
        elif number == 8:
            value = switch(data)
        elif number == 9:
            exact(data, 2)
            if data[0] & ~31:
                raise ProtocolError("Reserved CFG9 Q bits")
            value = QueryParameters(data[0] & 15, data[1], bool(data[0] & 16))
            encode_query(value)
        elif number == 10:
            value = TIDParameters(*exact(data, 2))
            encode_tid(value)
        elif number == 11:
            value = decode_mask(data)
        elif number == 31:
            exact(data, 6)
            value = tuple(int.from_bytes(data[p : p + 2], "big") for p in (0, 2, 4))
        else:
            value = bytes(data)
        return value
    except ValidationError as error:
        raise ProtocolError(str(error)) from error


def get_config(number: int, *, decoded=True) -> Request:
    integer(number, 0, 255, "CFG number")
    if number not in (7, 8, 9, 10, 11, 25, 29, 31):
        raise ValidationError("CFG number outside documented scope")
    return Request(0xEB, bytes((number,)), (lambda d: decode_config(number, d)) if decoded else raw)


def set_config(number: int, data: bytes, *, persist=False, confirmed_length=None) -> Request[None]:
    get_config(number)
    boolean(persist, "persist")
    if number in (25, 29):
        required = 6 if number == 25 else 5
        if confirmed_length != required:
            raise UnverifiedFeature(
                f"CFG{number} summary/detail length conflict; explicitly select {required}-byte dialect"
            )
        exact(data, required)
        if number == 25:
            if (
                data[0] != 15
                or not 1 <= data[1] <= 3
                or any(v > 3 for v in data[2:5])
                or data[5] > 1
            ):
                raise ValidationError("Invalid Impinj Scan fields")
        elif data[0] > 1 or data[1] > 3 or (data[0] and data[1] == 0):
            raise ValidationError("Invalid Impinj ScanID fields")
    else:
        decode_config(number, data)
    return Request(0xEA, bytes((0 if persist else 1, number)) + data, ack, True)


# ==============================================================================
# Commands: tag memory, selection and protection
# ==============================================================================

# Gen2 access builders; one RF command per write, no automatic retry/split.


ZERO_PASSWORD = b"\0" * 4


def password(value: bytes) -> bytes:
    return octets(value, "password", 4, 4)


def selection(target: TagTarget | None) -> tuple[bytes, bytes]:
    if target is None:
        return b"\x00", b""
    if not isinstance(target, TagTarget):
        raise ValidationError("target must be TagTarget or None")
    if target.epc is not None:
        return bytes((len(target.epc) // 2,)) + target.epc, b""
    return b"\xff", target.mask.encode()


def validate_access(bank: MemoryBank, address: int, count: int, maximum: int) -> None:
    integer(bank, 0, 3, "bank")
    integer(address, 0, 65535, "word_address")
    integer(count, 1, maximum, "word_count")
    if address + count > 65536:
        raise ValidationError("Operation exceeds the 16-bit word address space")


def read_memory(
    bank: MemoryBank,
    word_address: int,
    word_count: int,
    *,
    target: TagTarget | None = None,
    access_password=ZERO_PASSWORD,
    extended: bool | None = None,
) -> Request[bytes]:
    validate_access(bank, word_address, word_count, 120)
    if extended is not None:
        boolean(extended, "extended")
    ext = word_address > 255 if extended is None else extended
    integer(word_address, 0, 65535 if ext else 255, "word_address")
    prefix, mask = selection(target)
    data = prefix + bytes((bank,)) + word_address.to_bytes(2 if ext else 1, "big")
    data += bytes((word_count,)) + password(access_password) + mask
    return Request(0x15 if ext else 0x02, data, lambda d: exact(d, word_count * 2))


def write_memory(
    bank: MemoryBank,
    word_address: int,
    data: bytes,
    *,
    target: TagTarget | None = None,
    access_password=ZERO_PASSWORD,
    extended: bool | None = None,
    block=False,
) -> Request[None]:
    octets(data, "write data", 2, 242 if block else 64)
    if len(data) % 2:
        raise ValidationError("Write data must contain whole words")
    validate_access(bank, word_address, len(data) // 2, 121 if block else 32)
    if extended is not None:
        boolean(extended, "extended")
    boolean(block, "block")
    ext = word_address > 255 if extended is None else extended
    if block and ext:
        raise ValidationError("BlockWrite has only an 8-bit word pointer")
    integer(word_address, 0, 65535 if ext else 255, "word_address")
    prefix, mask = selection(target)
    payload = bytes((len(data) // 2,)) + prefix + bytes((bank,))
    payload += (
        word_address.to_bytes(2 if ext else 1, "big") + data + password(access_password) + mask
    )
    return Request(0x10 if block else 0x16 if ext else 0x03, payload, ack, True)


def block_erase(
    bank: MemoryBank,
    word_address: int,
    word_count: int,
    *,
    target: TagTarget | None = None,
    access_password=ZERO_PASSWORD,
) -> Request[None]:
    validate_access(bank, word_address, word_count, 120)
    integer(word_address, 1 if bank == MemoryBank.EPC else 0, 255, "word_address")
    prefix, mask = selection(target)
    payload = prefix + bytes((bank, word_address, word_count)) + password(access_password) + mask
    return Request(0x07, payload, ack, True)


def write_epc_single(epc: bytes, *, access_password=ZERO_PASSWORD) -> Request[None]:
    # Conservative intersection of the inconsistent ENum/WEPC paragraphs.
    octets(epc, "epc", 2, 28)
    if len(epc) % 2:
        raise ValidationError("EPC must contain whole words")
    return Request(0x04, bytes((len(epc) // 2,)) + password(access_password) + epc, ack, True)


def lock_tag(
    lock_target: int, protection: int, *, target: TagTarget, access_password=ZERO_PASSWORD
) -> Request[None]:
    if target is None:
        raise ValidationError("Lock requires an explicit tag target")
    prefix, mask = selection(target)
    data = (
        prefix
        + bytes(
            (integer(lock_target, 0, 4, "lock_target"), integer(protection, 0, 3, "protection"))
        )
        + password(access_password)
        + mask
    )
    return Request(0x06, data, ack, True)


def kill_tag(kill_password: bytes, *, target: TagTarget) -> Request[None]:
    if target is None:
        raise ValidationError("Kill requires an explicit tag target")
    pwd = password(kill_password)
    if pwd == ZERO_PASSWORD:
        raise ValidationError("Kill password cannot be zero")
    prefix, mask = selection(target)
    return Request(0x05, prefix + pwd + mask, ack, True)


def select_tag(
    mask: TagMask, *, antenna_mask: int, ports: int, select_target=4, action=0, truncate=False
) -> Request[None]:
    integer(antenna_mask, 1, (1 << ports) - 1, "antenna_mask")
    prefix = antenna_mask.to_bytes(2 if ports == 16 else 1, "big")
    prefix += bytes(
        (integer(select_target, 0, 4, "select_target"), integer(action, 0, 7, "action"))
    )
    return Request(
        0x9A, prefix + mask.encode() + bytes((boolean(truncate, "truncate"),)), ack, True
    )


def pc_with_epc_length(pc: bytes, epc: bytes) -> bytes:
    exact(pc, 2)
    octets(epc, "epc", 2, 62)
    if len(epc) % 2:
        raise ValidationError("EPC must contain whole words")
    # Preserve all eleven non-length bits, including UMI/XI/Toggle/AFI.
    return ((int.from_bytes(pc, "big") & 0x07FF) | ((len(epc) // 2) << 11)).to_bytes(2, "big")


# ==============================================================================
# Commands: explicit vendor-extension limits
# ==============================================================================

# Vendor tag commands are explicitly outside the default Gen2 SDK contract.
#
# NXP read-protection/EAS, Monza QT and EM4325 commands need an identified tag
# and dedicated evidence. Presence of an Ex10 radio does not prove tag support.
# FastID and TagFocus are exposed by inventory/extended with this same caveat.


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


# ==============================================================================
# Commands: inventory builders and report decoders
# ==============================================================================

# Answer/FastID/TID/Mix codecs, V2.25 8.2.1/14/21/22 and 8.4.41.


def validate_inventory(config: InventoryConfig, ports: int) -> None:
    if not isinstance(config, InventoryConfig) or not isinstance(config.data, InventoryData):
        raise ValidationError("Expected InventoryConfig with InventoryData enum")
    integer(config.q, 0, 15, "q")
    integer(config.session, 0, 255, "session")
    if config.session not in (0, 1, 2, 3, 253, 254, 255):
        raise ValidationError("Answer session must be 0..3,253,254,255")
    integer(config.target, 0, 1, "target")
    integer(config.antenna, 1, ports, "antenna")
    integer(config.scan_time_100ms, 0, 255, "scan_time_100ms")
    if config.scan_time_100ms in (1, 2):
        raise ValidationError("Scan time must be 0 or 3..255")
    for flag in ("phase", "statistics", "special_strategy"):
        boolean(getattr(config, flag), flag)
    if config.mask is not None and not isinstance(config.mask, TagMask):
        raise ValidationError("mask must be TagMask")
    if config.data is InventoryData.TID:
        integer(config.tid_word_address, 0, 255, "tid_word_address")
        integer(config.tid_word_count, 1, 15, "tid_word_count")
        if config.session > 3:
            raise ValidationError("TID requires session 0..3")
    if config.data is InventoryData.MIX:
        integer(config.memory_bank, 0, 3, "memory_bank")
        integer(config.word_address, 0, 65535, "word_address")
        integer(config.word_count, 1, 120, "word_count")
        if config.word_count > 31:
            raise UnverifiedFeature(
                "Mix Len bit6 collides with lengths >62 bytes; use read_memory for 32..120 words"
            )
        if config.word_address + config.word_count > 65536:
            raise ValidationError("Mix read exceeds address space")
        if config.special_strategy or config.session not in (0, 1, 2, 3, 255):
            raise ValidationError("Mix does not define special strategy/AUTO2/AUTO3")
        password(config.access_password)


def build_inventory(config: InventoryConfig, *, ports: int, buffered=False) -> Request:
    validate_inventory(config, ports)
    if buffered and (
        config.data not in (InventoryData.EPC, InventoryData.TID)
        or config.phase
        or config.statistics
        or config.session not in (0, 1, 2, 3, 255)
    ):
        raise ValidationError("Buffer inventory supports EPC/TID with no phase/statistics")
    q = config.q | (128 if config.statistics else 0) | (64 if config.special_strategy else 0)
    q |= (32 if config.data is InventoryData.FAST_ID else 0) | (16 if config.phase else 0)
    data = bytes((q, config.session))
    if config.mask is not None:
        data += config.mask.encode()
    if config.data is InventoryData.TID:
        data += bytes((config.tid_word_address, config.tid_word_count))
    elif config.data is InventoryData.MIX:
        data += bytes((config.memory_bank,)) + config.word_address.to_bytes(2, "big")
        data += bytes((config.word_count,)) + password(config.access_password)
    data += bytes((config.target, 0x80 + config.antenna - 1, config.scan_time_100ms))
    return Request(0x18 if buffered else 0x19 if config.data is InventoryData.MIX else 0x01, data)


def inventory_epc(mask_data: bytes, bit_length: int, bit_offset=0, *, exclude=False) -> Request:
    integer(bit_length, 1, 196, "bit_length")
    integer(bit_offset, 0, 495, "bit_offset")
    if bit_length + bit_offset > 496:
        raise ValidationError("EPC match exceeds 496 bits")
    mask = TagMask(1, bit_offset, bit_length, mask_data)
    return Request(
        0x1A,
        bytes((boolean(exclude, "exclude"),))
        + bit_length.to_bytes(2, "big")
        + bit_offset.to_bytes(2, "big")
        + mask.data,
    )


def fast_start(target=0) -> Request[None]:
    return Request(0x50, bytes((integer(target, 0, 1, "target"),)), ack, True)


def fast_stop() -> Request[None]:
    return Request(0x51, decode=ack, mutating=True)


def decode_statistics(data: bytes) -> InventoryStatistics:
    exact(data, 7)
    return InventoryStatistics(
        data[0], int.from_bytes(data[1:3], "big"), int.from_bytes(data[3:], "big")
    )


def _record(data, offset, *, allow_fastid):
    if offset >= len(data):
        raise ProtocolError("Missing tag length")
    flags = data[offset]
    size = flags & 63
    end = offset + 1 + size + 1 + (7 if flags & 64 else 0)
    if size < 2 or size % 2 or end > len(data) or (flags & 128 and not allow_fastid):
        raise ProtocolError("Invalid tag length/flags")
    value = data[offset + 1 : offset + 1 + size]
    measurements = _rssi_fields(data[offset + 1 + size])
    if flags & 64:
        tail = data[offset + size + 2 : end]
        measurements.update(phase_raw=tail[:4], frequency_khz=int.from_bytes(tail[4:], "big"))

        begin, end_phase = int.from_bytes(tail[:2], "big"), int.from_bytes(tail[2:4], "big")
        measurements.update(
            phase_begin_raw=begin,
            phase_end_raw=end_phase,
            phase_begin_degrees=phase_to_degrees(begin),
            phase_end_degrees=phase_to_degrees(end_phase),
            phase_begin_radians=phase_to_radians(begin),
            phase_end_radians=phase_to_radians(end_phase),
            phase_conversion=PHASE_CONVERSION,
        )
    return end, flags, value, measurements


def decode_answer(
    data: bytes, config: InventoryConfig, *, ports: int, received_at: float | None = None
) -> list[TagReport]:
    if len(data) < 2:
        raise ProtocolError("Missing inventory antenna/count")
    ant = decode_antenna(data[0], ports=ports) if data[1] else {}
    reports, offset = [], 2
    for _ in range(data[1]):
        start = offset
        offset, flags, value, measurements = _record(
            data, offset, allow_fastid=config.data is InventoryData.FAST_ID
        )
        epc, tid = None, None
        if flags & 128:
            if len(value) < 14:
                raise ProtocolError("FastID needs EPC plus twelve TID bytes")
            epc, tid = value[:-12], value[-12:]
        elif config.data is InventoryData.TID:
            if len(value) != 2 * config.tid_word_count:
                raise ProtocolError("TID report length differs from request")
            tid = value
        else:
            epc = value
        reports.append(
            TagReport(
                epc=epc,
                tid=tid,
                **ant,
                **measurements,
                received_at=received_at,
                raw=data[start:offset],
            )
        )
    if offset != len(data):
        raise ProtocolError("Trailing inventory data")
    return reports


class MixDecoder:
    """Pair only adjacent sequence numbers, including across frames and 127->0."""

    def __init__(self, config: InventoryConfig, ports: int):
        self.config, self.ports = config, ports
        self.pending: tuple[int, TagReport] | None = None
        self.missing_memory = 0
        self.orphan_memory = 0

    def feed(self, data: bytes, received_at=None) -> list[TagReport]:
        if len(data) < 2:
            raise ProtocolError("Missing Mix antenna/count")
        reports, offset = [], 2
        ant = decode_antenna(data[0], ports=self.ports) if data[1] else {}
        for _ in range(data[1]):
            if offset >= len(data):
                raise ProtocolError("Truncated Mix packet")
            packet, start = data[offset], offset
            offset, flags, value, measurements = _record(data, offset + 1, allow_fastid=False)
            seq = packet & 127
            if packet & 128:
                if len(value) != 2 * self.config.word_count:
                    raise ProtocolError("Mix memory length differs from request")
                if (
                    self.pending is not None
                    and seq == (self.pending[0] + 1) % 128
                    and self.pending[1].antenna_raw == data[0]
                ):
                    old = self.pending[1]
                    reports.append(
                        replace(
                            old,
                            memory_data=value,
                            memory_bank=self.config.memory_bank,
                            word_address=self.config.word_address,
                            raw=old.raw + data[start:offset],
                        )
                    )
                    self.pending = None
                else:
                    reports.extend(self.flush())
                    self.orphan_memory += 1
            else:
                reports.extend(self.flush())
                self.pending = (
                    seq,
                    TagReport(
                        epc=value,
                        **ant,
                        **measurements,
                        received_at=received_at,
                        raw=data[start:offset],
                    ),
                )
        if offset != len(data):
            raise ProtocolError("Trailing Mix bytes")
        return reports

    def flush(self) -> list[TagReport]:
        if self.pending is None:
            return []
        self.missing_memory += 1
        report = self.pending[1]
        self.pending = None
        return [report]


def decode_stream(
    data: bytes, *, ports: int, tid_words=0, received_at=None, scenario=True
) -> TagReport:
    if not data:
        raise ProtocolError("Missing stream antenna")
    ant = decode_antenna(data[0], ports=ports)
    if scenario:
        end, _, value, measurements = _record(data, 1, allow_fastid=False)
    else:
        if len(data) < 3:
            raise ProtocolError("Short real-time report")
        size = data[1]
        if not 2 <= size <= 62 or size % 2:
            raise ProtocolError("Invalid real-time identifier length")
        end, value = 3 + size, data[2 : 2 + size]
        if len(data) < end:
            raise ProtocolError("Truncated real-time report")
        measurements = _rssi_fields(data[2 + size])
    if end != len(data) or (tid_words and len(value) != tid_words * 2):
        raise ProtocolError("Stream report length/configuration mismatch")
    return TagReport(
        epc=None if tid_words else value,
        tid=value if tid_words else None,
        **ant,
        **measurements,
        received_at=received_at,
        raw=data,
    )


def decode_heartbeat(data: bytes, *, ports: int) -> Heartbeat:
    exact(data, 8 + ports)
    if any(v > 2 for v in data[4:-4]):
        raise ProtocolError("Invalid heartbeat antenna status")
    return Heartbeat(
        int.from_bytes(data[:4], "big"), tuple(data[4:-4]), int.from_bytes(data[-4:], "big")
    )


# ==============================================================================
# Commands: reader buffer
# ==============================================================================

# Reader buffer management; data kind is supplied from the inventory context.


def set_buffer_length(max_bytes: int) -> Request[None]:
    if max_bytes not in (16, 62):
        raise ValidationError("Buffer max_bytes must be 16 or 62; changing it clears buffer")
    return Request(0x70, bytes((0 if max_bytes == 16 else 1,)), ack, True)


def get_buffer_length() -> Request[int]:
    def decode(data):
        v = exact(data, 1)[0]
        if v not in (0, 1):
            raise ProtocolError("Invalid buffer length code")
        return 16 if v == 0 else 62

    return Request(0x71, decode=decode)


def clear_buffer() -> Request[None]:
    return Request(0x73, decode=ack, mutating=True)


def get_buffer_count() -> Request[int]:
    return Request(0x74, decode=u16)


def decode_counts(data: bytes) -> BufferCounts:
    exact(data, 4)
    return BufferCounts(int.from_bytes(data[:2], "big"), int.from_bytes(data[2:], "big"))


def decode_buffer(
    data: bytes, *, ports: int, data_kind=InventoryData.EPC, antenna_bytes: int | None = None
) -> list[TagReport]:
    if data_kind not in (InventoryData.EPC, InventoryData.TID):
        raise ValidationError("Buffer contains EPC or TID")
    if ports == 16 and antenna_bytes is None:
        raise UnverifiedFeature(
            "16-port buffer Ant width conflicts in manual; select verified width"
        )
    width = antenna_bytes or 1
    integer(width, 1, 2, "antenna_bytes")
    if not data:
        raise ProtocolError("Missing buffer count")
    reports, offset = [], 1
    for _ in range(data[0]):
        start = offset
        if offset + width + 1 > len(data):
            raise ProtocolError("Truncated buffer record")
        ant = int.from_bytes(data[offset : offset + width], "big")
        size = data[offset + width]
        offset += width + 1
        if size < 2 or size > 62 or size % 2 or offset + size + 2 > len(data):
            raise ProtocolError("Invalid buffer identifier length")
        value = data[offset : offset + size]
        offset += size
        reports.append(
            TagReport(
                epc=value if data_kind is InventoryData.EPC else None,
                tid=value if data_kind is InventoryData.TID else None,
                **decode_antenna(ant, ports=ports, mask_encoding=True),
                **_rssi_fields(data[offset]),
                read_count=data[offset + 1],
                raw=data[start : offset + 2],
            )
        )
        offset += 2
    if offset != len(data):
        raise ProtocolError("Trailing buffer bytes")
    return reports


# ==============================================================================
# Commands: GPIO, indicator and buzzer
# ==============================================================================

# LED/buzzer/GPIO control, limited to documented two output pins.


def set_buzzer(enabled: bool) -> Request[None]:
    return Request(0x40, bytes((boolean(enabled, "enabled"),)), ack, True)


def indicator(active_50ms: int, silent_50ms: int, count: int) -> Request[None]:
    return Request(
        0x33,
        bytes(
            (
                integer(active_50ms, 0, 255, "active_50ms"),
                integer(silent_50ms, 0, 255, "silent_50ms"),
                integer(count, 0, 255, "count"),
            )
        ),
        ack,
        True,
    )


def set_gpio(output1: bool, output2: bool) -> Request[None]:
    value = boolean(output1, "output1") | (boolean(output2, "output2") << 1)
    return Request(0x46, bytes((value,)), ack, True)


def decode_gpio(data: bytes) -> GPIOState:
    v = exact(data, 1)[0]
    if v & ~0x31:
        raise ProtocolError("GPIO response has reserved bits")
    return GPIOState(bool(v & 1), bool(v & 16), bool(v & 32), v)


def get_gpio() -> Request[GPIOState]:
    return Request(0x47, decode=decode_gpio)


# ==============================================================================
# Commands: temperature and return loss
# ==============================================================================

# Temperature and return loss have documented units; RSSI does not.


def decode_temperature(data: bytes) -> int:
    exact(data, 2)
    if data[0] not in (0, 1):
        raise ProtocolError("Invalid temperature sign")
    return data[1] * (1 if data[0] else -1)


def get_temperature() -> Request[int]:
    return Request(0x92, decode=decode_temperature)


def measure_return_loss(frequency_khz: int, antenna: int, *, ports: int) -> Request[int]:
    integer(frequency_khz, 840000, 960000, "frequency_khz")
    if frequency_khz % 100 and frequency_khz % 125:
        raise ValidationError("Frequency must be a multiple of 100 or 125 kHz")
    integer(antenna, 1, min(ports, 4), "antenna (documented diagnostic range)")
    return Request(0x91, frequency_khz.to_bytes(4, "big") + bytes((antenna - 1,)), u8)


def return_loss_threshold(threshold_db: int | None = None) -> Request[int]:
    value = 0 if threshold_db is None else 128 | integer(threshold_db, 0, 20, "threshold_db")

    def decode(data):
        n = u8(data)
        if n > 20:
            raise ProtocolError("Invalid return-loss threshold")
        return n

    return Request(0x6E, bytes((value,)), decode, threshold_db is not None)


# ==============================================================================
# Dispatcher: single RX owner, deadlines and response routing
# ==============================================================================

# One RX task and one ordinary request. No transaction IDs, no unsafe retry.


@dataclass
class _Pending:
    command: int
    future: asyncio.Future
    terminal: Callable[[ResponseFrame], bool]
    on_frame: Callable[[ResponseFrame], None] | None
    frames: list[ResponseFrame] = field(default_factory=list)
    transmitted: bool = False
    exchange_id: int = 0


class Dispatcher:
    """Timeout/cancellation after TX poisons this connection until explicit recovery.

    open(recover=True) is an assertion by the caller that the old device operation
    has ended and stale bytes cannot arrive (e.g. physical reset/reconnection).
    Closing a port alone does not stop reader RF.
    """

    def __init__(self, transport: AsyncTransport, *, address=0, max_frames=4096, on_event=None):
        self.transport = transport
        self.address = integer(address, 0, 255, "address")
        self.max_frames = integer(max_frames, 1, 1000000, "max_frames")
        self.parser = FrameParser()
        self._lock = asyncio.Lock()
        self._tx_lock = asyncio.Lock()
        self._pending: _Pending | None = None
        self._rx_task: asyncio.Task | None = None
        self.opened = False
        self.fault: Exception | None = None
        self.on_notification: Callable[[ResponseFrame], None] | None = None
        self.on_fault: Callable[[Exception], None] | None = None
        self.unsolicited: list[ResponseFrame] = []
        self.last_exchange_error: ExchangeError | None = None
        self.trace = TraceEmitter(on_event)
        self._exchange_sequence = 0

    @property
    def pending_command(self) -> int | None:
        return self._pending.command if self._pending else None

    async def open(self, *, recover=False) -> None:
        if self.opened:
            if self.fault:
                raise StateError("Close and establish a clean device boundary before recovery")
            return
        if self.fault and not recover:
            raise StateError(
                "Unknown prior command state; explicit open(recover=True) requires resynchronization"
            )
        try:
            await self.transport.open()
        except BaseException:
            await self.transport.close()
            raise
        self.parser.reset()
        self.fault = None
        self.opened = True
        self._rx_task = asyncio.create_task(self._receive(), name="zk-rfid-rx")
        self.trace.emit("connected", address=self.address)

    async def close(self) -> None:
        self.opened = False
        if self._pending:
            self._fail(TransportError("Connection closed while a command was pending"))
        task, self._rx_task = self._rx_task, None
        if task:
            task.cancel()
        try:
            await self.transport.close()
        finally:
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self.trace.emit("disconnected", address=self.address)

    def _check(self):
        if not self.opened:
            raise StateError("Reader is closed")
        if self.fault is not None:
            raise StateError(f"Connection is desynchronized: {self.fault}")

    def _fail(self, error: Exception):
        if self.fault is None:
            self.fault = error
            self.trace.emit("fault", detail=f"{type(error).__name__}: {error}")
        p = self._pending
        if p and not p.future.done():
            wrapped = ExchangeError(str(error), frames=p.frames, transmitted=p.transmitted)
            p.future.set_exception(wrapped)
        if self.on_fault is not None:
            self.on_fault(error)

    async def _write_all(self, wire: bytes, *, exchange_id=None) -> None:
        async with self._tx_lock:
            offset = 0
            while offset < len(wire):
                count = await self.transport.write(wire[offset:])
                if (
                    isinstance(count, bool)
                    or not isinstance(count, int)
                    or not 0 < count <= len(wire) - offset
                ):
                    raise TransportError("Invalid/zero transport write count")
                self.trace.emit(
                    "tx",
                    exchange_id=exchange_id,
                    command=wire[2],
                    address=wire[1],
                    raw=wire[offset : offset + count],
                    detail="transport-accepted bytes",
                )
                offset += count

    async def exchange(
        self,
        command: int,
        data: bytes = b"",
        *,
        timeout=3.0,
        deadline: float | None = None,
        terminal=None,
        on_frame=None,
    ) -> tuple[ResponseFrame, ...]:
        wire = encode_command(self.address, command, data)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (float, int))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be finite positive seconds")
        loop = asyncio.get_running_loop()
        end = loop.time() + timeout if deadline is None else deadline
        if not math.isfinite(end) or end <= loop.time():
            raise RequestTimeout("Deadline expired before TX", transmitted=False)
        p = None
        try:
            async with asyncio.timeout_at(end):
                async with self._lock:
                    self._check()
                    if loop.time() >= end:
                        raise RequestTimeout(
                            "Deadline expired while waiting for request lock", transmitted=False
                        )
                    self._exchange_sequence += 1
                    p = _Pending(
                        command,
                        loop.create_future(),
                        terminal or (lambda f: True),
                        on_frame,
                        exchange_id=self._exchange_sequence,
                    )
                    self._pending = p  # Register before the first TX byte.
                    self.trace.emit(
                        "request",
                        exchange_id=p.exchange_id,
                        command=command,
                        address=self.address,
                        raw=wire,
                    )
                    try:
                        p.transmitted = True  # Even a failed/short write may reach the module.
                        await self._write_all(wire, exchange_id=p.exchange_id)
                        return await asyncio.shield(p.future)
                    finally:
                        if self._pending is p:
                            self._pending = None
        except asyncio.CancelledError:
            if p and p.transmitted:
                error = ExchangeError(
                    "Host cancelled; device operation may continue",
                    frames=p.frames,
                    transmitted=True,
                )
                self.last_exchange_error = error
                self.trace.emit(
                    "cancelled", exchange_id=p.exchange_id, command=command, detail=str(error)
                )
                self._fail(error)
            raise
        except TimeoutError as cause:
            error = RequestTimeout(
                "Host deadline expired",
                frames=p.frames if p else (),
                transmitted=p.transmitted if p else False,
            )
            self.last_exchange_error = error
            self.trace.emit(
                "timeout",
                exchange_id=p.exchange_id if p else None,
                command=command,
                detail=str(error),
            )
            if p and p.transmitted:
                self._fail(error)
            raise error from cause
        except (StateError, ValueError):
            raise
        except Exception as cause:
            error = (
                cause
                if isinstance(cause, ExchangeError)
                else ExchangeError(
                    str(cause),
                    frames=p.frames if p else (),
                    transmitted=p.transmitted if p else False,
                )
            )
            self.last_exchange_error = error
            if p and p.transmitted:
                self._fail(error)
            raise error from cause
        finally:
            if p and not p.future.done():
                p.future.cancel()
            elif p and not p.future.cancelled():
                p.future.exception()  # Retrieve errors when TX itself failed before awaiting RX.

    async def interrupt_answer(self, *, timeout=1.0) -> bool:
        """Send 0x93 only while 0x01 is pending; it has no independent ACK."""
        self._check()
        p = self._pending
        if p is None or p.command != 0x01 or p.future.done():
            return False
        try:
            async with asyncio.timeout(timeout):
                # Do not acquire the ordinary request lock: inventory owns it.
                self.trace.emit(
                    "interrupt",
                    exchange_id=p.exchange_id,
                    command=0x93,
                    detail="Interrupt pending 0x01; no independent ACK",
                )
                await self._write_all(encode_command(self.address, 0x93), exchange_id=p.exchange_id)
        except BaseException as cause:
            self._fail(TransportError("Unable to transmit inventory interrupt"))
            raise cause
        return True

    async def _receive(self):
        try:
            while self.opened:
                chunk = await self.transport.read(4096)
                if not isinstance(chunk, bytes):
                    raise TransportError("Transport.read must return bytes")
                if not chunk:
                    raise TransportError("Transport EOF")
                self.trace.emit("rx", raw=chunk, detail="transport read chunk")
                discarded_before = self.parser.diagnostics.discarded_bytes
                parsed = self.parser.feed(chunk)
                if self.parser.diagnostics.discarded_bytes != discarded_before:
                    self.trace.emit(
                        "parser_loss",
                        detail=str(self.parser.diagnostics.discarded_bytes - discarded_before),
                    )
                for frame in parsed:
                    active = self._pending
                    self.trace.emit(
                        "frame",
                        exchange_id=active.exchange_id
                        if active and frame.command != 0xEE
                        else None,
                        command=frame.command,
                        address=frame.address,
                        status=frame.status,
                        raw=frame.raw,
                    )
                    if self.address != 255 and frame.address != self.address:
                        self._unexpected(frame, poison=False)
                        continue
                    if frame.command == 0xEE:
                        if self.on_notification is not None:
                            self.on_notification(frame)
                        else:
                            self._unexpected(frame, poison=False)
                        continue
                    p = self._pending
                    if p is None or p.future.done():
                        self._unexpected(frame, poison=True)
                        continue
                    if frame.command != p.command and not (
                        frame.command == 0 and frame.status == 0xFE
                    ):
                        self._unexpected(frame, poison=True)
                        continue
                    if self.address == 255:
                        self.address = frame.address  # Single point-to-point reader only.
                    if len(p.frames) >= self.max_frames:
                        raise ProtocolError("Exchange frame limit exceeded")
                    p.frames.append(frame)
                    if p.on_frame:
                        p.on_frame(frame)
                    if p.terminal(frame):
                        p.future.set_result(tuple(p.frames))
                        self.trace.emit(
                            "response_complete",
                            exchange_id=p.exchange_id,
                            command=p.command,
                            status=frame.status,
                        )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._fail(error)

    def _unexpected(self, frame, *, poison):
        self.trace.emit(
            "unexpected",
            command=frame.command,
            status=frame.status,
            address=frame.address,
            raw=frame.raw,
            detail="connection invalidated" if poison else "not matched",
        )
        self.parser.diagnostics.unexpected_frames += 1
        self.unsolicited.append(frame)
        if len(self.unsolicited) > 32:
            del self.unsolicited[0]
        if poison:
            self._fail(
                ProtocolError(f"Unexpected response 0x{frame.command:02X}; stale reply possible")
            )


# ==============================================================================
# Inventory sessions: Answer, Scenario and Real-time
# ==============================================================================

# Inventory lifecycle; only Dispatcher reads bytes from the transport.


def _outcome(reports, status, stats, diagnostics, *, reason=None, unknown=False, partial=False):
    failure = status is not None and status not in (1, 2, 4, 0x26, 0xFB)
    incomplete = unknown or partial or failure or status in (2, 4)
    outcome = (
        Outcome.PARTIAL
        if reports and incomplete
        else Outcome.UNKNOWN
        if unknown
        else Outcome.FAILURE
        if failure
        else Outcome.PARTIAL
        if incomplete
        else Outcome.SUCCESS
    )
    return InventoryOutcome(
        tuple(reports),
        reason
        or {
            1: "completed",
            2: "device_timeout",
            4: "buffer_full",
            0xFB: "no_tag",
            0x26: "statistics",
        }.get(status, "device_error"),
        outcome,
        status,
        not incomplete,
        stats,
        tuple(diagnostics),
        len(reports),
    )


async def collect_answer(reader, config, *, timeout, request=None, managed=False, on_report=None):
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValidationError("timeout must be finite positive seconds")
    request = request or build_inventory(config, ports=reader.capabilities.antenna_ports)
    validate_inventory(config, reader.capabilities.antenna_ports)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    reports, messages = [], []
    statistics, final_status = None, None
    decoder = (
        MixDecoder(config, reader.capabilities.antenna_ports)
        if config.data is InventoryData.MIX
        else None
    )
    before_loss = reader.dispatcher.parser.diagnostics.discarded_bytes
    done = loop.create_future()
    result = None
    unknown = False

    def receive(frame):
        nonlocal statistics, final_status
        if frame.status == 0x26:
            statistics = decode_statistics(frame.data)
            if final_status is None:
                final_status = 0x26
        elif frame.status in (1, 2, 3, 4):
            decoded = (
                decoder.feed(frame.data, loop.time())
                if decoder
                else decode_answer(
                    frame.data,
                    config,
                    ports=reader.capabilities.antenna_ports,
                    received_at=loop.time(),
                )
            )
            if len(reports) + len(decoded) > 65536:
                raise QueueOverflow("Answer inventory exceeds 65536 reports")
            reports.extend(decoded)
            if on_report:
                for report in decoded:
                    on_report(report)
            if frame.status != 3:
                final_status = frame.status
        else:
            final_status = frame.status
            if frame.status != 0xFB:
                status = interpret_status(frame.command, frame.status, frame.data)
                messages.append(
                    status.name
                    + (f": tag_error={status.tag_error}" if status.tag_error is not None else "")
                )
            elif frame.data:
                raise ProtocolError("No-tag response unexpectedly contains data")

    def terminal(frame):
        if frame.status == 3:
            return False
        if config.statistics and frame.status in (1, 2, 4):
            return False
        return True

    async with reader._operation(deadline):
        reader._guard(request.command, internal=managed)
        reader.state = ReaderState.INVENTORYING
        reader._answer_done = done
        try:
            await reader.dispatcher.exchange(
                request.command,
                request.data,
                timeout=timeout,
                deadline=deadline,
                terminal=terminal,
                on_frame=receive,
            )
        except asyncio.CancelledError:
            unknown = True
            messages.append("Host cancelled; reader may still be inventorying")
            raise
        except ExchangeError as error:
            unknown = error.transmitted
            messages.append(str(error))
        finally:
            if decoder:
                remaining = decoder.flush()
                reports.extend(remaining)
                if on_report:
                    for report in remaining:
                        on_report(report)
                if decoder.missing_memory or decoder.orphan_memory:
                    messages.append(
                        f"Mix missing_memory={decoder.missing_memory}, orphan_memory={decoder.orphan_memory}"
                    )
            lost = reader.dispatcher.parser.diagnostics.discarded_bytes - before_loss
            if lost:
                messages.append(f"Parser discarded {lost} bytes")
            result = _outcome(
                reports,
                final_status,
                statistics,
                messages,
                reason="host_incomplete" if unknown else None,
                unknown=unknown,
                partial=bool(
                    lost or (decoder and (decoder.missing_memory or decoder.orphan_memory))
                ),
            )
            reader.state = (
                ReaderState.UNKNOWN
                if reader.dispatcher.fault
                else ReaderState.INVENTORYING
                if managed
                else ReaderState.IDLE
            )
            reader.last_inventory_outcome = result
            if not done.done():
                done.set_result(result)
            reader._answer_done = None
    return result


async def collect_buffer(reader, data_kind, timeout):
    deadline = asyncio.get_running_loop().time() + timeout
    reports, messages, status, unknown = [], [], None, False
    caps = reader.capabilities
    # Validate ambiguous hardware layout before sending.
    decode_buffer(
        b"\0",
        ports=caps.antenna_ports,
        data_kind=data_kind,
        antenna_bytes=caps.buffer_antenna_bytes,
    )

    def receive(frame):
        nonlocal status
        status = frame.status
        if status in (1, 3):
            reports.extend(
                decode_buffer(
                    frame.data,
                    ports=caps.antenna_ports,
                    data_kind=data_kind,
                    antenna_bytes=caps.buffer_antenna_bytes,
                )
            )
            if len(reports) > 65536:
                raise QueueOverflow("Reader buffer response exceeds 65536 reports")
        else:
            messages.append(interpret_status(frame.command, status, frame.data).name)

    async with reader._operation(deadline):
        reader._guard(0x72)
        before = reader.dispatcher.parser.diagnostics.discarded_bytes
        try:
            await reader.dispatcher.exchange(
                0x72,
                timeout=timeout,
                deadline=deadline,
                terminal=lambda f: f.status != 3,
                on_frame=receive,
            )
        except asyncio.CancelledError:
            reader.last_inventory_outcome = _outcome(
                reports, status, None, ["Host cancelled buffer read"], unknown=True
            )
            raise
        except ExchangeError as error:
            unknown = error.transmitted
            messages.append(str(error))
        lost = reader.dispatcher.parser.diagnostics.discarded_bytes - before
        if lost:
            messages.append(f"Parser discarded {lost} bytes")
    return _outcome(reports, status, None, messages, unknown=unknown, partial=bool(lost))


class InventorySession:
    """Async iterator of TagReport or Heartbeat with explicit stop and final outcome.

    Scenario applies volatile CFG9/10/11 and one antenna, verifies them, and
    restores snapshots after a confirmed stop. Real-time uses the already saved
    0x75 configuration; 0x76 start/stop changes persistent working mode.
    Stream outcome stores counters; the consumer owns delivered report storage.
    """

    def __init__(self, reader, mode, config, *, queue_size=1024, trigger=False):
        if not isinstance(mode, InventoryMode):
            raise ValidationError("mode must be InventoryMode")
        integer(queue_size, 1, 1000000, "queue_size")
        validate_inventory(
            replace(config, session=0) if mode is InventoryMode.SCENARIO else config,
            reader.capabilities.antenna_ports,
        )
        if mode is not InventoryMode.ANSWER and config.data not in (
            InventoryData.EPC,
            InventoryData.TID,
        ):
            raise UnsupportedFeature(
                "Scenario/Real-time do not have a verified FastID/Mix contract"
            )
        if mode is InventoryMode.SCENARIO:
            reader.capabilities.require("ex10")
            encode_query(QueryParameters(config.q, config.session, config.phase))
            if config.statistics or config.special_strategy:
                raise UnsupportedFeature(
                    "Scenario does not use Answer statistics/special-strategy flags"
                )
        if mode is InventoryMode.REAL_TIME:
            reader.capabilities.require("realtime")
            if config.phase or config.statistics or config.special_strategy:
                raise UnsupportedFeature("Real-time 0xEE has no verified phase/statistics flags")
        self.reader, self.mode, self.config = reader, mode, config
        self.trigger = trigger
        self.queue = asyncio.Queue(maxsize=queue_size)
        self._finished = asyncio.Event()
        self._stopping = asyncio.Event()
        self._stop_lock = asyncio.Lock()
        self._task = None
        self._error = None
        self._snapshots = []
        self._started = False
        self._closed = False
        self._stop_ack = False
        self._tid_words = 0
        self._received = 0
        self._dropped = 0
        self._heartbeats = 0
        self._messages = []
        self._start_discarded = 0
        self.outcome: InventoryOutcome | None = None

    async def start(self):
        reader = self.reader
        async with reader._operation():
            reader._guard(
                0x50
                if self.mode is InventoryMode.SCENARIO
                else 0x76
                if self.mode is InventoryMode.REAL_TIME
                else 0x01
            )
            if reader._session is not None:
                raise StateError("An inventory session already owns this reader")
            reader._session = self
            reader.state = ReaderState.STARTING
            self._start_discarded = reader.dispatcher.parser.diagnostics.discarded_bytes
            if self.mode is InventoryMode.ANSWER:
                reader.state = ReaderState.INVENTORYING
                self._started = True
                self._task = asyncio.create_task(self._answer_loop(), name="zk-answer-session")
                return self
            reader.dispatcher.on_notification = self._notification
            try:
                if self.mode is InventoryMode.SCENARIO:
                    await self._prepare_scenario()
                    request = fast_start(self.config.target)
                else:
                    current = (
                        await reader._execute(get_working_mode(), internal=True, locked=True)
                    ).require_success()
                    reader._working_mode = current.mode
                    self._tid_words = current.config.tid_word_count
                    expected = InventoryData.TID if self._tid_words else InventoryData.EPC
                    if self.config.data is not expected:
                        raise ValidationError(
                            "Real-time data kind differs from saved 0x75 configuration"
                        )
                    request = set_working_mode(
                        WorkingMode.TRIGGER if self.trigger else WorkingMode.REAL_TIME
                    )
                # Mark before TX, because failure/timeout can leave RF running.
                self._started = True
                result = await reader._execute(request, internal=True, locked=True)
                result.require_success()
                if self.mode is InventoryMode.REAL_TIME:
                    reader._working_mode = (
                        WorkingMode.TRIGGER if self.trigger else WorkingMode.REAL_TIME
                    )
                reader.state = ReaderState.INVENTORYING
            except BaseException as error:
                self._error = error
                # If Start was rejected with a definitive response, RF did not start.
                definite_rejection = (
                    isinstance(error, OperationError) and error.result.outcome is Outcome.FAILURE
                )
                if not self._started or definite_rejection:
                    self._started = False
                    if reader.dispatcher.fault is None:
                        await self._restore()
                self._finished.set()
                reader._session = None
                reader.state = (
                    ReaderState.UNKNOWN
                    if self._started or reader.dispatcher.fault
                    else ReaderState.IDLE
                )
                raise
        return self

    async def _prepare_scenario(self):
        reader, cfg = self.reader, self.config
        self._tid_words = cfg.tid_word_count if cfg.data is InventoryData.TID else 0
        desired = [
            (9, encode_query(QueryParameters(cfg.q, cfg.session, cfg.phase))),
            (10, encode_tid(TIDParameters(cfg.tid_word_address, self._tid_words))),
            (11, (cfg.mask or TagMask(1, 32, 0, b"")).encode()),
        ]
        # Get all snapshots before making any change.
        snapshots = []
        for number, data in desired:
            old = (
                await reader._execute(get_config(number, decoded=False), internal=True, locked=True)
            ).require_success()
            snapshots.append((number, old, data))
        ports = reader.capabilities.antenna_ports
        old_ant = None
        if ports > 1:
            if ports > 8:
                raise UnsupportedFeature(
                    "Scenario auto-restore needs a verified 16-port antenna mask getter"
                )
            info = (
                await reader._execute(get_reader_info(), internal=True, locked=True)
            ).require_success()
            old_ant = info.antenna_raw
            set_antennas(old_ant, ports=ports)  # Prevalidate restoration.
        for number, old, data in snapshots:
            if old == data:
                continue
            self._snapshots.append(Request(0xEA, bytes((1, number)) + old, ack, True))
            (
                await reader._execute(set_config(number, data), internal=True, locked=True)
            ).require_success()
            checked = (
                await reader._execute(get_config(number, decoded=False), internal=True, locked=True)
            ).require_success()
            if checked != data:
                raise ProtocolError(f"CFG{number} read-back mismatch before start")
        if old_ant is not None and old_ant != 1 << (cfg.antenna - 1):
            self._snapshots.append(set_antennas(old_ant, ports=ports))
            (
                await reader._execute(
                    set_antennas(1 << (cfg.antenna - 1), ports=ports),
                    internal=True,
                    locked=True,
                )
            ).require_success()

    async def _restore(self):
        reader = self.reader
        errors = []
        while self._snapshots:
            request = self._snapshots.pop()
            try:
                result = await reader._execute(request, internal=True, locked=True)
                result.require_success()
                if request.command == 0xEA:
                    actual = (
                        await reader._execute(
                            get_config(request.data[1], decoded=False),
                            internal=True,
                            locked=True,
                        )
                    ).require_success()
                    if actual != request.data[2:]:
                        raise ProtocolError("Configuration restoration read-back mismatch")
                elif request.command == 0x3F:
                    actual = (
                        await reader._execute(get_reader_info(), internal=True, locked=True)
                    ).require_success()
                    expected = (
                        request.data[0] & 15
                        if len(request.data) == 1
                        else int.from_bytes(request.data[1:], "big")
                    )
                    if actual.antenna_raw != expected:
                        raise ProtocolError("Antenna restoration read-back mismatch")
            except Exception as error:
                errors.append(str(error))
                if reader.dispatcher.fault:
                    break
        if errors:
            error = ProtocolError("Restoration failed: " + "; ".join(errors))
            self._messages.append(str(error))
            reader.dispatcher._fail(error)
            self._error = self._error or error

    def _notification(self, frame):
        try:
            pending = self.reader.dispatcher._pending
            ack_in_same_chunk = (
                pending
                and pending.command in (0x51, 0x76)
                and pending.future.done()
                and self._stopping.is_set()
            )
            if self._stop_ack or ack_in_same_chunk:
                # Do not attribute late frames to the next inventory generation.
                raise ProtocolError("Tag/heartbeat after stop ACK; stream boundary is unverified")
            if frame.status == 0x28:
                value = decode_heartbeat(frame.data, ports=self.reader.capabilities.antenna_ports)
                self._heartbeats += 1
            elif frame.status == 0:
                value = decode_stream(
                    frame.data,
                    ports=self.reader.capabilities.antenna_ports,
                    tid_words=self._tid_words,
                    received_at=asyncio.get_running_loop().time(),
                    scenario=self.mode is InventoryMode.SCENARIO,
                )
                self._received += 1
            else:
                raise ProtocolError(f"Unexpected streaming status 0x{frame.status:02X}")
            self._enqueue(value)
        except Exception as error:
            self._fault(error)
            if isinstance(error, ProtocolError) and not isinstance(error, QueueOverflow):
                self.reader.dispatcher._fail(error)

    def _enqueue(self, value):
        try:
            self.queue.put_nowait(value)
        except asyncio.QueueFull:
            self._dropped += 1
            self._fault(
                QueueOverflow(
                    "Inventory queue overflow; stop and increase queue/consumer throughput"
                )
            )

    def _fault(self, error):
        self._error = self._error or error
        self._finished.set()

    async def _answer_loop(self):
        def receive(report):
            self._received += 1
            self._enqueue(report)

        try:
            while not self._stopping.is_set() and not self._error:
                result = await collect_answer(
                    self.reader,
                    self.config,
                    timeout=self.reader._timeout(scan_time_100ms=self.config.scan_time_100ms),
                    managed=True,
                    on_report=receive,
                )
                if not result.complete:
                    self._messages.extend(result.diagnostics or (result.termination_reason,))
                if self.reader.dispatcher.fault:
                    break
                await asyncio.sleep(0)  # Yield even for immediate fake/in-memory responses.
        except Exception as error:
            self._fault(error)
        finally:
            self._finished.set()

    async def stop(self) -> InventoryOutcome:
        async with self._stop_lock:
            if self._closed:
                return self.outcome
            self._stopping.set()
            reader = self.reader
            reader.state = (
                ReaderState.STOPPING if not reader.dispatcher.fault else ReaderState.UNKNOWN
            )
            if self.mode is InventoryMode.ANSWER:
                if reader.dispatcher.pending_command == 0x01 and not reader.dispatcher.fault:
                    await reader.dispatcher.interrupt_answer()
                if self._task:
                    await self._task  # Mix has no 0x93; its bounded round must finish.
                self._stop_ack = not bool(reader.dispatcher.fault)
            else:
                async with reader._operation():
                    if not reader.dispatcher.fault and self._started:
                        request = (
                            fast_stop()
                            if self.mode is InventoryMode.SCENARIO
                            else set_working_mode(WorkingMode.ANSWER)
                        )
                        result = await reader._execute(request, internal=True, locked=True)
                        if result.ok and not reader.dispatcher.fault:
                            self._stop_ack = True
                            if self.mode is InventoryMode.REAL_TIME:
                                reader._working_mode = WorkingMode.ANSWER
                            await self._restore()
                        else:
                            self._fault(OperationError(result))
            lost = reader.dispatcher.parser.diagnostics.discarded_bytes - self._start_discarded
            if lost:
                self._messages.append(f"Parser discarded {lost} bytes")
            if self._error:
                self._messages.append(str(self._error))
            uncertain = not self._stop_ack or bool(reader.dispatcher.fault)
            partial = bool(self._messages or self._dropped)
            self.outcome = InventoryOutcome(
                termination_reason="stop_unconfirmed" if uncertain else "stopped",
                outcome=Outcome.UNKNOWN
                if uncertain
                else Outcome.PARTIAL
                if partial
                else Outcome.SUCCESS,
                complete=not uncertain and not partial,
                diagnostics=tuple(self._messages),
                received_count=self._received,
                dropped_count=self._dropped,
            )
            self._closed = True
            self._finished.set()
            reader._session = None
            reader.state = ReaderState.UNKNOWN if uncertain else ReaderState.IDLE
            # Retain the callback after stop to detect illegal late 0xEE frames.
            return self.outcome

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.queue.empty():
            return self.queue.get_nowait()
        if self._finished.is_set():
            if self._error:
                raise self._error
            raise StopAsyncIteration
        get_task = asyncio.create_task(self.queue.get())
        end_task = asyncio.create_task(self._finished.wait())
        try:
            done, _ = await asyncio.wait((get_task, end_task), return_when=asyncio.FIRST_COMPLETED)
            if get_task in done:
                return get_task.result()
            if self._error:
                raise self._error
            raise StopAsyncIteration
        finally:
            for task in (get_task, end_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(get_task, end_task, return_exceptions=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()


# ==============================================================================
# ZKReader: public native SDK API
# ==============================================================================

# Native async ZK public API. Construction/import never opens a device.


class ZKReader:
    def __init__(
        self, transport: AsyncTransport, *, address=0, capabilities=None, timeout=3.0, on_event=None
    ):
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValidationError("timeout must be finite positive seconds")
        self.capabilities = capabilities or ReaderCapabilities()
        self.dispatcher = Dispatcher(transport, address=address, on_event=on_event)
        self.timeout = timeout
        self.state = ReaderState.DISCONNECTED
        self._operation_lock = asyncio.Lock()
        self._active_deadline = None
        self._session = None
        self.last_result: CommandResult | None = None
        self._working_mode = None  # Unknown until queried; do not claim a cached mode.
        self.dispatcher.on_fault = self._on_fault

    @property
    def state(self) -> ReaderState:
        """Host lifecycle state; IDLE alone does not prove a saved real-time mode is off."""
        return self._state

    @state.setter
    def state(self, value: ReaderState) -> None:
        previous = getattr(self, "_state", None)
        self._state = value
        if previous != value:
            self.dispatcher.trace.emit(
                "state", detail=f"{previous.value if previous else 'new'} -> {value.value}"
            )

    @property
    def address(self) -> int:
        """Current wire address; changes only after an acknowledged address update."""
        return self.dispatcher.address

    @property
    def is_inventory_running(self) -> bool:
        """Whether this host owns an active or transitioning inventory session."""
        return self.state in (ReaderState.STARTING, ReaderState.INVENTORYING, ReaderState.STOPPING)

    def get_capabilities(self) -> ReaderCapabilities:
        """Return declared capabilities and their evidence; no hardware probing."""
        return self.capabilities

    def _timeout(self, value=None, *, scan_time_100ms=None):
        chosen = self.timeout if value is None else value
        if (
            isinstance(chosen, bool)
            or not isinstance(chosen, (int, float))
            or not math.isfinite(chosen)
            or chosen <= 0
        ):
            raise ValidationError("timeout must be finite positive seconds")
        if value is None and scan_time_100ms is not None:
            chosen = max(chosen, scan_time_100ms * 0.1 + 0.25)
        return chosen

    @asynccontextmanager
    async def _operation(self, deadline=None):
        end = asyncio.get_running_loop().time() + self.timeout if deadline is None else deadline
        try:
            async with asyncio.timeout_at(end):
                await self._operation_lock.acquire()
        except TimeoutError as error:
            raise RequestTimeout(
                "Deadline expired before acquiring reader operation lock", transmitted=False
            ) from error
        self._active_deadline = end
        try:
            yield
        finally:
            self._active_deadline = None
            self._operation_lock.release()

    def _on_fault(self, error):
        self.state = ReaderState.UNKNOWN
        if self._session is not None:
            self._session._fault(error)

    async def open(self, *, recover: bool = False) -> "ZKReader":
        """Open transport and start the single RX task; recover requires a known clean boundary."""
        already_open = self.dispatcher.opened
        await self.dispatcher.open(recover=recover)
        if not already_open:
            self.state = ReaderState.IDLE
            self._working_mode = None
        return self

    async def close(self) -> None:
        """Stop owned inventory, close transport and join background tasks."""
        session = self._session
        try:
            if self._session is not None and self.dispatcher.fault is None:
                await self._session.stop()
            elif self.dispatcher.pending_command == 0x01 and self.dispatcher.fault is None:
                await self.stop_inventory()
        finally:
            if self._session is not None:
                self._session._fault(StateError("Reader closed"))
            await self.dispatcher.close()
            if session is not None and session._task is not None:
                if not session._task.done():
                    session._task.cancel()
                await asyncio.gather(session._task, return_exceptions=True)
            self._session = None
            self.state = ReaderState.DISCONNECTED

    async def __aenter__(self):
        return await self.open()

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def _guard(self, command, internal=False):
        if self.state is ReaderState.DISCONNECTED:
            raise StateError("Open reader first")
        if self.state is ReaderState.UNKNOWN:
            raise StateError("Reader state unknown; resynchronization is required")
        if not internal and self.is_inventory_running:
            if (
                self._session
                and self._session.mode is InventoryMode.REAL_TIME
                and command in (0x21, 0x77)
            ):
                return
            raise StateError("Stop inventory before changing reader/tag configuration")
        if self._working_mode in (WorkingMode.REAL_TIME, WorkingMode.TRIGGER) and command not in (
            0x21,
            0x76,
            0x77,
        ):
            raise StateError("Real-time firmware accepts only info, working-mode set/get")

    async def _execute(
        self, request: Request[T], *, deadline=None, internal=False, locked=False
    ) -> CommandResult[T]:
        if not locked:
            async with self._operation(deadline):
                return await self._execute(
                    request, deadline=deadline, internal=internal, locked=True
                )
        self._guard(request.command, internal)
        deadline = self._active_deadline if deadline is None else deadline
        try:
            frames = await self.dispatcher.exchange(
                request.command, request.data, timeout=self.timeout, deadline=deadline
            )
        except asyncio.CancelledError:
            self.last_result = CommandResult(
                Outcome.UNKNOWN,
                command=request.command,
                confirmation=Confirmation.TRANSMITTED,
                diagnostics=("Cancelled; operation may continue",),
            )
            raise
        except ExchangeError as error:
            result = CommandResult(
                Outcome.UNKNOWN if error.transmitted else Outcome.FAILURE,
                command=request.command,
                confirmation=Confirmation.TRANSMITTED if error.transmitted else Confirmation.NONE,
                diagnostics=(str(error),),
            )
        else:
            frame = frames[-1]
            status = interpret_status(frame.command, frame.status, frame.data)
            decoded, outcome, messages = None, status.outcome, ()
            if status.outcome is Outcome.SUCCESS:
                try:
                    decoded = request.decode(frame.data)
                except ProtocolError as error:
                    outcome = Outcome.UNKNOWN if request.mutating else Outcome.FAILURE
                    messages = (str(error),)
            else:
                messages = (status.name,)
            result = CommandResult(
                outcome,
                decoded,
                request.command,
                frame.status,
                status.tag_error,
                frame.data,
                Confirmation.ACKNOWLEDGED,
                messages,
            )
        self.last_result = result
        self.dispatcher.trace.emit(
            "result",
            exchange_id=self.dispatcher._exchange_sequence
            if result.confirmation is not Confirmation.NONE
            else None,
            command=result.command,
            status=result.status,
            detail=f"{result.outcome.value}; {result.confirmation.value}; {'; '.join(result.diagnostics)}",
        )
        return result

    async def get_reader_info(self) -> CommandResult[ReaderInfo]:
        """Read native reader identity, RF configuration and antenna-check state (0x21)."""
        result = await self._execute(get_reader_info())
        if result.ok:
            result = replace(result, data=replace(result.data, address=self.address))
            self.last_result = result
        return result

    async def get_serial_number(self) -> CommandResult[bytes]:
        """Read the four-byte reader serial number (0x4C)."""
        return await self._execute(get_serial_number())

    async def get_power(self) -> CommandResult[tuple[int, ...]]:
        """Read one integer dBm value per declared antenna (0x94)."""
        return await self._execute(get_power(ports=self.capabilities.antenna_ports))

    async def set_power(
        self, power_dbm: int | tuple[int, ...], *, persist: bool = False
    ) -> CommandResult[None]:
        """Set 0..30 dBm globally or per antenna; volatile unless persist=True (0x2F)."""
        return await self._execute(
            set_power(power_dbm, ports=self.capabilities.antenna_ports, persist=persist)
        )

    async def get_write_power(self) -> CommandResult[WritePower]:
        """Get write power. Returns native status and confirmation."""
        return await self._execute(get_write_power())

    async def set_write_power(self, power_dbm: int | None) -> CommandResult[None]:
        """Set separate write power in dBm, or None to disable it (0x79)."""
        return await self._execute(set_write_power(power_dbm))

    async def get_write_retries(self) -> CommandResult[int]:
        """Get write retries. Returns native status and confirmation."""
        return await self._execute(write_retries())

    async def set_write_retries(self, count: int) -> CommandResult[int]:
        """Set the module retry count 0..7; the host never retries writes (0x7B)."""
        return await self._execute(write_retries(count))

    async def set_antennas(self, mask: int, *, persist: bool = False) -> CommandResult[None]:
        """Select antenna mask with bit0=port1; volatile unless persist=True (0x3F)."""
        return await self._execute(
            set_antennas(mask, ports=self.capabilities.antenna_ports, persist=persist)
        )

    async def get_antennas(self) -> CommandResult[int]:
        """Get the native antenna mask; the 16-port getter remains unverified."""
        if self.capabilities.antenna_ports > 8:
            raise UnverifiedFeature("Reader-info antenna byte does not specify full 16-port mask")
        result = await self.get_reader_info()
        return replace(result, data=result.data.antenna_raw if result.ok else None)

    async def set_antenna_check(self, enabled: bool) -> CommandResult[None]:
        """Set antenna check. Returns native status and confirmation."""
        return await self._execute(set_antenna_check(enabled))

    async def get_antenna_check(self) -> CommandResult[bool]:
        """Get antenna check. Returns native status and confirmation."""
        result = await self.get_reader_info()
        return replace(result, data=result.data.antenna_check if result.ok else None)

    async def set_address(self, address: int) -> CommandResult[None]:
        """Change reader address after receiving the ACK at the original address (0x24)."""
        request = set_address(address)
        async with self._operation():
            result = await self._execute(request, locked=True)
            if result.ok:
                self.dispatcher.address = address  # ACK uses original address.
            return result

    async def set_baudrate(self, baudrate: int) -> CommandResult[None]:
        """Receive ACK at the old baud, then switch the transport baud (0x28)."""
        request = set_baudrate(baudrate)
        setter = getattr(self.dispatcher.transport, "set_baudrate", None)
        if setter is None:
            raise ValidationError(
                "Transport must implement async set_baudrate to switch both endpoints"
            )
        async with self._operation():
            result = await self._execute(request, locked=True)
            if result.ok:
                try:
                    await setter(baudrate)  # ACK is received at the old baud.
                except BaseException:
                    self.dispatcher._fail(
                        StateError("Module baud changed but transport update failed")
                    )
                    raise
            return result

    async def set_inventory_time(self, scan_time_100ms: int) -> CommandResult[None]:
        """Set native scan time in 100 ms units: 0 or 3..255 (0x25)."""
        return await self._execute(set_scan_time(scan_time_100ms))

    async def set_interface(self, interface: str) -> CommandResult[None]:
        """Select usb or uart (0x6A); effective after a module power cycle."""
        return await self._execute(set_interface(interface))

    async def get_region(self) -> CommandResult[Region]:
        """Get region. Returns native status and confirmation."""
        return await self._execute(get_region())

    async def set_region(
        self, region: Region, *, persist: bool = False, legacy: bool = False
    ) -> CommandResult[None]:
        """Set native region and channel indices; no NATION region-ID conversion (0x22)."""
        return await self._execute(set_region(region, persist=persist, legacy=legacy))

    async def get_profile(self, *, extended_format: bool = True) -> CommandResult[int]:
        """Read native RF profile ID, including the 16-bit Ex10 format (0x7F)."""
        return await self._execute(profile(extended=extended_format))

    async def set_profile(
        self, profile_id: int, *, persist: bool = False, extended_format: bool = True
    ) -> CommandResult[int]:
        """Set native RF profile ID; no inferred equivalence with NATION profiles (0x7F)."""
        return await self._execute(profile(profile_id, persist=persist, extended=extended_format))

    async def get_drm(self) -> CommandResult[bool]:
        """Get drm. Returns native status and confirmation."""
        return await self._execute(drm())

    async def set_drm(self, enabled: bool) -> CommandResult[bool]:
        """Set drm. Returns native status and confirmation."""
        return await self._execute(drm(enabled))

    async def set_buzzer(self, enabled: bool) -> CommandResult[None]:
        """Set buzzer. Returns native status and confirmation."""
        return await self._execute(set_buzzer(enabled))

    async def pulse_indicator(
        self, active_50ms: int, silent_50ms: int, count: int
    ) -> CommandResult[None]:
        """Pulse LED/buzzer using 50 ms active/silent units (0x33)."""
        return await self._execute(indicator(active_50ms, silent_50ms, count))

    async def get_gpio(self) -> CommandResult[GPIOState]:
        """Read input and output bits in the documented GPIO layout (0x47)."""
        self.capabilities.require("gpio")
        return await self._execute(get_gpio())

    async def set_gpio(self, output1: bool, output2: bool) -> CommandResult[None]:
        """Set the two documented GPO outputs (0x46)."""
        self.capabilities.require("gpio")
        return await self._execute(set_gpio(output1, output2))

    async def get_temperature(self) -> CommandResult[int]:
        """Read signed integer Celsius using the native sign byte (0x92)."""
        self.capabilities.require("temperature")
        return await self._execute(get_temperature())

    async def measure_return_loss(self, frequency_khz: int, antenna: int = 1) -> CommandResult[int]:
        """Measure return loss at a documented grid frequency in kHz (0x91)."""
        return await self._execute(
            measure_return_loss(frequency_khz, antenna, ports=self.capabilities.antenna_ports)
        )

    async def get_return_loss_threshold(self) -> CommandResult[int]:
        """Get return loss threshold. Returns native status and confirmation."""
        return await self._execute(return_loss_threshold())

    async def set_return_loss_threshold(self, threshold_db: int) -> CommandResult[int]:
        """Set return loss threshold. Returns native status and confirmation."""
        return await self._execute(return_loss_threshold(threshold_db))

    async def get_config(
        self, number: int, *, decoded: bool = True
    ) -> CommandResult[
        ScanParameters | QueryParameters | TIDParameters | TagMask | tuple[int, ...] | bool | bytes
    ]:
        """Read an Ex10 CFG value; decoded=False preserves the exact native bytes (0xEB)."""
        self.capabilities.require("ex10")
        return await self._execute(get_config(number, decoded=decoded))

    async def set_config(
        self, number: int, data: bytes, *, persist: bool = False
    ) -> CommandResult[None]:
        """Validate and set Ex10 CFG; ambiguous CFG25/29 require an explicit dialect (0xEA)."""
        self.capabilities.require("ex10")
        length = (
            self.capabilities.cfg25_length
            if number == 25
            else self.capabilities.cfg29_length
            if number == 29
            else None
        )
        return await self._execute(
            set_config(number, data, persist=persist, confirmed_length=length)
        )

    async def get_scan_parameters(self) -> CommandResult[ScanParameters]:
        """Get scan parameters. Returns native status and confirmation."""
        return await self.get_config(7)

    async def set_scan_parameters(
        self, parameters: ScanParameters, *, persist: bool = False
    ) -> CommandResult[None]:
        """Set scan parameters. Returns native status and confirmation."""
        return await self.set_config(7, encode_scan(parameters), persist=persist)

    async def get_tag_focus(self) -> CommandResult[bool]:
        """Get tag focus. Returns native status and confirmation."""
        return await self.get_config(8)

    async def set_tag_focus(self, enabled: bool, *, persist: bool = False) -> CommandResult[None]:
        """Set tag focus. Returns native status and confirmation."""
        return await self.set_config(8, bytes((boolean(enabled, "enabled"),)), persist=persist)

    async def get_query_parameters(self) -> CommandResult[QueryParameters]:
        """Get query parameters. Returns native status and confirmation."""
        return await self.get_config(9)

    async def set_query_parameters(
        self, parameters: QueryParameters, *, persist: bool = False
    ) -> CommandResult[None]:
        """Set query parameters. Returns native status and confirmation."""
        return await self.set_config(9, encode_query(parameters), persist=persist)

    async def get_tid_parameters(self) -> CommandResult[TIDParameters]:
        """Get tid parameters. Returns native status and confirmation."""
        return await self.get_config(10)

    async def set_tid_parameters(
        self, parameters: TIDParameters, *, persist: bool = False
    ) -> CommandResult[None]:
        """Set tid parameters. Returns native status and confirmation."""
        return await self.set_config(10, encode_tid(parameters), persist=persist)

    async def get_inventory_mask(self) -> CommandResult[TagMask]:
        """Get inventory mask. Returns native status and confirmation."""
        return await self.get_config(11)

    async def set_inventory_mask(
        self, mask: TagMask | None, *, persist: bool = False
    ) -> CommandResult[None]:
        """Set inventory mask. Returns native status and confirmation."""
        data = (mask or TagMask(MemoryBank.EPC, 32, 0, b"")).encode()
        return await self.set_config(11, data, persist=persist)

    async def get_custom_profiles(self) -> CommandResult[tuple[int, ...]]:
        """Get custom profiles. Returns native status and confirmation."""
        return await self.get_config(31)

    async def set_custom_profiles(
        self, profile_ids: tuple[int, int, int], *, persist: bool = False
    ) -> CommandResult[None]:
        """Set custom profiles. Returns native status and confirmation."""
        return await self.set_config(31, encode_profiles(profile_ids), persist=persist)

    async def set_real_time_config(self, config: RealTimeConfig) -> CommandResult[None]:
        """Persist the dedicated 0x75 real-time settings; separate from Scenario CFG."""
        self.capabilities.require("realtime")
        return await self._execute(set_real_time(config))

    async def get_working_mode(self) -> CommandResult[WorkingModeConfig]:
        """Read the 0x77 mode and fixed-width saved real-time configuration."""
        result = await self._execute(get_working_mode())
        if result.ok:
            self._working_mode = result.data.mode
        return result

    async def set_working_mode(self, mode: WorkingMode) -> CommandResult[None]:
        """Persistent mode setting. For managed 0xEE delivery use start_inventory()."""
        request = set_working_mode(mode)
        async with self._operation():
            result = await self._execute(request, locked=True)
            if result.ok:
                self._working_mode = WorkingMode(mode)
            return result

    async def get_heartbeat_interval(self) -> CommandResult[int]:
        """Get heartbeat interval. Returns native status and confirmation."""
        return await self._execute(heartbeat())

    async def set_heartbeat_interval(self, interval_30s: int) -> CommandResult[int]:
        """Set heartbeat interval in 30 second units, with 0 disabling it (0x78)."""
        return await self._execute(heartbeat(interval_30s))

    async def get_buffer_length(self) -> CommandResult[int]:
        """Get buffer length. Returns native status and confirmation."""
        return await self._execute(get_buffer_length())

    async def set_buffer_length(self, max_bytes: int) -> CommandResult[None]:
        """Set maximum stored EPC/TID length to 16 or 62 bytes; clears the buffer (0x70)."""
        return await self._execute(set_buffer_length(max_bytes))

    async def get_buffer_count(self) -> CommandResult[int]:
        """Get buffer count. Returns native status and confirmation."""
        return await self._execute(get_buffer_count())

    async def clear_buffer(self) -> CommandResult[None]:
        """Clear the reader tag buffer (0x73)."""
        return await self._execute(clear_buffer())

    async def inventory_to_buffer(
        self, config: InventoryConfig = InventoryConfig(), *, timeout: float | None = None
    ) -> CommandResult[BufferCounts]:
        """Run buffered inventory and return counts; this changes reader buffer contents (0x18)."""
        request = build_inventory(config, ports=self.capabilities.antenna_ports, buffered=True)
        deadline = asyncio.get_running_loop().time() + self._timeout(
            timeout, scan_time_100ms=config.scan_time_100ms
        )
        return await self._execute(replace(request, decode=decode_counts), deadline=deadline)

    async def read_buffer(
        self, *, data_kind: InventoryData = InventoryData.EPC, timeout: float | None = None
    ) -> InventoryOutcome:
        """Collect all 0x72 frames; preserve partial reports and enforce one overall deadline."""

        return await collect_buffer(self, data_kind, self._timeout(timeout))

    async def inventory_once(
        self, config: InventoryConfig = InventoryConfig(), *, timeout: float | None = None
    ) -> InventoryOutcome:
        """Run one Answer/Mix round, preserving reports on partial completion or timeout."""

        return await collect_answer(
            self, config, timeout=self._timeout(timeout, scan_time_100ms=config.scan_time_100ms)
        )

    async def inventory_single(self, *, timeout: float | None = None) -> InventoryOutcome:
        """Run native single-tag inventory (0x0F)."""

        return await collect_answer(
            self, InventoryConfig(), timeout=self._timeout(timeout), request=Request(0x0F)
        )

    async def inventory_matching_epc(
        self,
        data: bytes,
        bit_length: int,
        *,
        bit_offset: int = 0,
        exclude: bool = False,
        timeout: float | None = None,
    ) -> InventoryOutcome:
        """Run native EPC-bit-match inventory with explicit bit offset and length (0x1A)."""

        request = inventory_epc(data, bit_length, bit_offset, exclude=exclude)
        return await collect_answer(
            self, InventoryConfig(), timeout=self._timeout(timeout), request=request
        )

    async def start_inventory(
        self,
        mode: InventoryMode = InventoryMode.SCENARIO,
        *,
        config: InventoryConfig = InventoryConfig(),
        queue_size: int = 1024,
        trigger: bool = False,
    ) -> InventorySession:
        """Start a managed async report iterator; stop explicitly or use its context manager."""

        session = InventorySession(self, mode, config, queue_size=queue_size, trigger=trigger)
        await session.start()
        return session

    async def stop_inventory(self) -> InventoryOutcome:
        """Stop by mode-specific semantics; 0x93 has no ACK of its own."""
        if self._session is not None:
            return await self._session.stop()
        if self.dispatcher.pending_command == 0x01:
            # collect_answer owns the request; wait for its normal completion.
            await self.dispatcher.interrupt_answer()
            task = getattr(self, "_answer_done", None)
            if task is not None:
                return await asyncio.shield(task)
        if self.is_inventory_running:
            raise StateError("This inventory opcode has no asynchronous stop command")
        return InventoryOutcome(termination_reason="already_idle")

    async def read_memory(
        self,
        bank: MemoryBank,
        word_address: int,
        word_count: int,
        *,
        target: TagTarget | None = None,
        access_password: bytes = ZERO_PASSWORD,
        extended_format: bool | None = None,
    ) -> CommandResult[bytes]:
        """Read 1..120 16-bit words; choose extended address format automatically when needed."""
        return await self._execute(
            read_memory(
                bank,
                word_address,
                word_count,
                target=target,
                access_password=access_password,
                extended=extended_format,
            )
        )

    def _verification_target(self, target, bank, address, count, verification_target):
        chosen = verification_target or target
        if chosen is None:
            raise ValidationError("Read-back verification requires an explicit target")
        if verification_target is None and target is not None:
            if target.epc is not None and bank == MemoryBank.EPC:
                raise ValidationError(
                    "Provide a post-write verification_target when changing EPC/PC"
                )
            if target.mask is not None and target.mask.bank == bank:
                lo, hi = target.mask.bit_address, target.mask.bit_address + target.mask.bit_length
                if max(lo, address * 16) < min(hi, (address + count) * 16):
                    raise ValidationError(
                        "Write changes target mask; supply a post-write verification_target"
                    )
        return chosen

    async def write_memory(
        self,
        bank: MemoryBank,
        word_address: int,
        data: bytes,
        *,
        target: TagTarget | None = None,
        access_password: bytes = ZERO_PASSWORD,
        extended_format: bool | None = None,
        verify: bool = False,
        verification_target: TagTarget | None = None,
        verification_password: bytes | None = None,
        timeout: float | None = None,
    ) -> CommandResult[bytes | None]:
        """Write 1..32 words once, optionally verify using a stable post-write target."""
        request = write_memory(
            bank,
            word_address,
            data,
            target=target,
            access_password=access_password,
            extended=extended_format,
        )
        boolean(verify, "verify")
        read_request = None
        if verify:
            selected = self._verification_target(
                target, bank, word_address, len(data) // 2, verification_target
            )
            if (
                bank == MemoryBank.RESERVED
                and word_address < 4
                and word_address + len(data) // 2 > 2
                and verification_password is None
            ):
                raise ValidationError("Access-password write requires verification_password")
            pwd = access_password if verification_password is None else verification_password
            read_request = read_memory(
                bank, word_address, len(data) // 2, target=selected, access_password=pwd
            )
        deadline = asyncio.get_running_loop().time() + self._timeout(timeout)
        async with self._operation(deadline):
            written = await self._execute(request, deadline=deadline, locked=True)
            if not written.ok or not verify:
                return written
            try:
                checked = await self._execute(read_request, deadline=deadline, locked=True)
            except asyncio.CancelledError:
                self._cancelled_write((written,))
                raise
            result = self._verified_write(written, checked, data)
            self.last_result = result
            return result

    def _verified_write(self, written, checked, expected):
        if checked.ok and checked.data == expected:
            return replace(
                written,
                data=expected,
                confirmation=Confirmation.READ_BACK,
                steps=(written, checked),
            )
        return replace(
            written,
            outcome=Outcome.PARTIAL,
            data=checked.data,
            steps=(written, checked),
            diagnostics=("Write acknowledged but read-back failed or mismatched",)
            + checked.diagnostics,
        )

    def _cancelled_write(self, confirmed_steps):
        """Retain acknowledged writes when cancellation interrupts later verification."""
        interrupted = self.last_result
        self.last_result = replace(
            confirmed_steps[-1],
            outcome=Outcome.PARTIAL,
            steps=(*confirmed_steps, interrupted),
            diagnostics=("Write acknowledged; host cancelled before verification completed",),
        )

    async def write_epc(
        self,
        epc: bytes,
        *,
        target: TagTarget,
        access_password: bytes = ZERO_PASSWORD,
        verify: bool = True,
        verification_target: TagTarget | None = None,
        timeout: float | None = None,
    ) -> CommandResult[bytes | None]:
        """Read PC, preserve non-length bits, then one targeted PC+EPC write."""
        pc_with_epc_length(b"\0\0", epc)
        selection(target)
        if target is None:
            raise ValidationError(
                "Targeted write_epc requires a target; use write_epc_single for 0x04"
            )
        boolean(verify, "verify")
        selected = (
            self._verification_target(
                target, MemoryBank.EPC, 1, 1 + len(epc) // 2, verification_target
            )
            if verify
            else None
        )
        deadline = asyncio.get_running_loop().time() + self._timeout(timeout)
        async with self._operation(deadline):
            pc = await self._execute(
                read_memory(MemoryBank.EPC, 1, 1, target=target, access_password=access_password),
                deadline=deadline,
                locked=True,
            )
            if not pc.ok:
                return pc
            desired = pc_with_epc_length(pc.data, epc) + epc
            try:
                written = await self._execute(
                    write_memory(
                        MemoryBank.EPC, 1, desired, target=target, access_password=access_password
                    ),
                    deadline=deadline,
                    locked=True,
                )
            except asyncio.CancelledError:
                self.last_result = replace(self.last_result, steps=(pc, self.last_result))
                raise
            if not written.ok or not verify:
                self.last_result = replace(written, steps=(pc, written))
                return self.last_result
            try:
                checked = await self._execute(
                    read_memory(
                        MemoryBank.EPC,
                        1,
                        len(desired) // 2,
                        target=selected,
                        access_password=access_password,
                    ),
                    deadline=deadline,
                    locked=True,
                )
            except asyncio.CancelledError:
                self._cancelled_write((pc, written))
                raise
            result = replace(
                self._verified_write(written, checked, desired), steps=(pc, written, checked)
            )
            self.last_result = result
            return result

    async def write_epc_single(
        self, epc: bytes, *, access_password: bytes = ZERO_PASSWORD
    ) -> CommandResult[None]:
        """Native 0x04. Requires exactly one tag physically in the RF field."""
        return await self._execute(write_epc_single(epc, access_password=access_password))

    async def set_access_password(
        self,
        new_password: bytes,
        *,
        target: TagTarget,
        access_password: bytes = ZERO_PASSWORD,
        verify: bool = True,
    ) -> CommandResult[bytes | None]:
        """Write the 32-bit Access password, then verify using the new password if requested."""
        password(new_password)
        return await self.write_memory(
            MemoryBank.RESERVED,
            2,
            new_password,
            target=target,
            access_password=access_password,
            verify=verify,
            verification_password=new_password,
        )

    async def set_kill_password(
        self,
        new_password: bytes,
        *,
        target: TagTarget,
        access_password: bytes = ZERO_PASSWORD,
        verify: bool = True,
    ) -> CommandResult[bytes | None]:
        """Write the 32-bit Kill password; does not execute Kill or Lock."""
        password(new_password)
        return await self.write_memory(
            MemoryBank.RESERVED,
            0,
            new_password,
            target=target,
            access_password=access_password,
            verify=verify,
        )

    async def lock_tag(
        self,
        lock_target: int,
        protection: int,
        *,
        target: TagTarget,
        access_password: bytes = ZERO_PASSWORD,
    ) -> CommandResult[None]:
        """Apply native Gen2 protection to a specified target; permanent states are irreversible."""
        return await self._execute(
            lock_tag(lock_target, protection, target=target, access_password=access_password)
        )

    async def kill_tag(self, kill_password: bytes, *, target: TagTarget) -> CommandResult[None]:
        """Execute irreversible Gen2 Kill on an explicit target with a nonzero 32-bit password."""
        return await self._execute(kill_tag(kill_password, target=target))

    async def block_write(
        self,
        bank: MemoryBank,
        word_address: int,
        data: bytes,
        *,
        target: TagTarget | None = None,
        access_password: bytes = ZERO_PASSWORD,
    ) -> CommandResult[None]:
        """Use native BlockWrite within its independent frame budget; tag support is required."""
        return await self._execute(
            write_memory(
                bank, word_address, data, target=target, access_password=access_password, block=True
            )
        )

    async def block_erase(
        self,
        bank: MemoryBank,
        word_address: int,
        word_count: int,
        *,
        target: TagTarget | None = None,
        access_password: bytes = ZERO_PASSWORD,
    ) -> CommandResult[None]:
        """Erase 1..120 words using native BlockErase; tag support is required."""
        return await self._execute(
            block_erase(
                bank, word_address, word_count, target=target, access_password=access_password
            )
        )

    async def select_tag(
        self,
        mask: TagMask,
        *,
        antenna_mask: int = 1,
        select_target: int = 4,
        action: int = 0,
        truncate: bool = False,
    ) -> CommandResult[None]:
        """Apply native Gen2 Select using a bit-addressed mask, target, action and antenna mask."""
        return await self._execute(
            select_tag(
                mask,
                antenna_mask=antenna_mask,
                ports=self.capabilities.antenna_ports,
                select_target=select_target,
                action=action,
                truncate=truncate,
            )
        )


# ==============================================================================
# NATION API value mapping
# ==============================================================================

# Explicit value conversions. RF IDs, RSSI and phase are never guessed.


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


# ==============================================================================
# NATION async API adapter
# ==============================================================================

# Familiar NATION operation names with an explicit async ZK result contract.
#
# Not a drop-in for blocking/threaded nrn.py. Never imports the reference driver,
# builds NATION frames, or substitutes numeric RF identifiers.


class NationAdapter:
    def __init__(self, reader):
        self.reader = reader

    async def open(self):
        return await self.reader.open()

    async def close(self):
        return await self.reader.close()

    def get_sdk_info(self):

        return {"name": SDK_NAME, "version": SDK_VERSION, "adapter": "NATION async operations"}

    async def Query_Reader_Information(self):
        return await self.reader.get_reader_info()

    async def query_rfid_ability(self):
        return self.reader.get_capabilities()

    async def query_reader_power(self):
        result = await self.reader.get_power()
        return replace(result, data=power_dict(result.data) if result.ok else None)

    async def configure_reader_power(
        self, antenna_powers: dict[int, int], persistence: bool = False
    ):
        if not isinstance(antenna_powers, dict) or not antenna_powers:
            raise ValidationError("antenna_powers must be a nonempty dictionary")
        boolean(persistence, "persistence")
        reader = self.reader
        for port, dbm in antenna_powers.items():
            integer(port, 1, reader.capabilities.antenna_ports, "antenna")
            integer(dbm, 0, 30, "ZK power_dbm")
        async with reader._operation():
            before = await reader._execute(
                get_power(ports=reader.capabilities.antenna_ports), locked=True
            )
            if not before.ok:
                return before
            desired = list(before.data)
            for port, dbm in antenna_powers.items():
                desired[port - 1] = dbm
            result = await reader._execute(
                set_power(
                    tuple(desired), ports=reader.capabilities.antenna_ports, persist=persistence
                ),
                locked=True,
            )
            return replace(result, steps=(before, result))

    def build_antenna_mask(self, antenna_ids: list[int]) -> int:
        if not antenna_ids or len(set(antenna_ids)) != len(antenna_ids):
            raise ValidationError("Antenna IDs must be nonempty and unique")
        for port in antenna_ids:
            integer(port, 1, self.reader.capabilities.antenna_ports, "antenna")
        return sum(1 << (p - 1) for p in antenna_ids)

    async def save_antenna_mask(self, antenna_mask: int):
        return await self.reader.set_antennas(antenna_mask, persist=True)

    async def query_enabled_ant_mask(self):
        return await self.reader.get_antennas()

    async def _change_antenna(self, ant_id, enabled, save):
        reader = self.reader
        ports = reader.capabilities.antenna_ports
        integer(ant_id, 1, ports, "ant_id")
        if ports > 8:
            raise UnsupportedFeature("Full antenna readback not verified for 16 ports")
        async with reader._operation():
            before = await reader._execute(get_reader_info(), locked=True)
            if not before.ok:
                return before
            mask = before.data.antenna_raw
            mask = mask | (1 << (ant_id - 1)) if enabled else mask & ~(1 << (ant_id - 1))
            result = await reader._execute(
                set_antennas(mask, ports=ports, persist=save), locked=True
            )
            return replace(result, steps=(before, result))

    async def enable_ant(self, ant_id: int, save=False):
        return await self._change_antenna(ant_id, True, save)

    async def disable_ant(self, ant_id: int, save=False):
        return await self._change_antenna(ant_id, False, save)

    def is_inventory_running(self):
        return self.reader.is_inventory_running

    async def start_inventory_with_mode(
        self, antenna_ids: list[int], *, mode=InventoryMode.SCENARIO, config=InventoryConfig()
    ):
        mask = self.build_antenna_mask(antenna_ids)
        if mask & (mask - 1):
            raise UnsupportedFeature("This adapter stream contract selects one antenna per session")
        return await self.reader.start_inventory(
            mode, config=replace(config, antenna=antenna_ids[0])
        )

    async def run_inventory(
        self, antenna_ids: list[int], callback, *, duration: float, mode=InventoryMode.SCENARIO
    ):
        """Callbacks run in the consumer task, outside RX; callback failure stops RF."""
        if not callable(callback) or not isinstance(duration, (int, float)) or duration <= 0:
            raise ValidationError("Provide callback and a positive duration in seconds")
        session = await self.start_inventory_with_mode(antenna_ids, mode=mode)
        try:
            async with asyncio.timeout(duration):
                async for report in session:
                    if not isinstance(report, TagReport):
                        continue
                    result = callback(tag_dict(report))
                    if inspect.isawaitable(result):
                        await result
        except TimeoutError:
            pass
        finally:
            outcome = await session.stop()
        return outcome

    async def stop_inventory(self):
        return await self.reader.stop_inventory()

    async def write_epc_to_target_auto(
        self, target_tag_epc: str, new_epc_hex: str, *, access_pwd=0, timeout=3.0, verify=True
    ):
        old, new = hex_epc(target_tag_epc), hex_epc(new_epc_hex)
        if len(old) > 30 or len(new) > 30:
            raise UnsupportedFeature(
                "Adapter exact EPC target supports 1..15 words; use native stable TID mask for longer EPC"
            )
        integer(access_pwd, 0, 0xFFFFFFFF, "access_pwd")
        return await self.reader.write_epc(
            new,
            target=TagTarget(epc=old),
            access_password=access_pwd.to_bytes(4, "big"),
            verify=verify,
            verification_target=TagTarget(epc=new),
            timeout=timeout,
        )

    async def select_profile(
        self, profile_id: int, *, mapping: RFMapping | None = None, persist=False
    ):
        if mapping is None:
            unsupported("rf_profile")
        return await self.reader.set_profile(mapping.require(profile_id), persist=persist)

    async def get_profile(self):
        """Result contains a native ZK ID; no NATION equivalence is implied."""
        return await self.reader.get_profile()

    async def query_rf_band(self):
        """Result contains native Region fields, not NATION band codes."""
        return await self.reader.get_region()

    async def set_rf_band(self, band_code: int, persist=True):
        unsupported("rf_band")

    async def set_beeper(self, mode: int):
        integer(mode, 0, 2, "mode")
        if mode == 1:
            raise UnsupportedFeature("NATION beep-after-inventory is not ZK beep-on-every-tag")
        return await self.reader.set_buzzer(mode == 2)

    async def get_beeper(self):
        unsupported("beeper_query")

    async def set_filter_settings(self, repeated_time_ms=0, rssi_threshold=0):
        unsupported("native_filter")

    async def get_session(self):
        result = await self.reader.get_query_parameters()
        return replace(result, data=result.data.session if result.ok else None)


# Public integration API (low-level helpers remain explicitly importable).
__all__ = [
    "rssi_to_dbm",
    "phase_to_degrees",
    "phase_to_radians",
    "ZKReader",
    "TraceEvent",
    "ReaderCapabilities",
    "InventorySession",
    "AsyncTransport",
    "CommandResult",
    "Outcome",
    "Confirmation",
    "ReaderState",
    "ReaderInfo",
    "MemoryBank",
    "TagMask",
    "TagTarget",
    "TagReport",
    "InventoryConfig",
    "InventoryData",
    "InventoryMode",
    "InventoryOutcome",
    "InventoryStatistics",
    "Heartbeat",
    "Region",
    "GPIOState",
    "RealTimeConfig",
    "WorkingMode",
    "WorkingModeConfig",
    "WritePower",
    "ScanParameters",
    "QueryParameters",
    "TIDParameters",
    "LockTarget",
    "LockProtection",
    "BufferCounts",
    "ZKError",
    "ValidationError",
    "ProtocolError",
    "StateError",
    "TransportError",
    "ExchangeError",
    "RequestTimeout",
    "UnsupportedFeature",
    "UnverifiedFeature",
    "QueueOverflow",
    "DeviceError",
    "OperationError",
    "setup_logging",
    "SDK_NAME",
    "SDK_VERSION",
    "__version__",
    "SerialTransport",
    "NationAdapter",
    "RFMapping",
    "Equivalence",
    "RFProfile",
    "PROFILES",
    "get_profile_definition",
    "Request",
    "Dispatcher",
    "TraceEmitter",
    "ParserDiagnostics",
    "FrameParser",
    "ResponseFrame",
    "Command",
    "ConfigID",
    "StatusInfo",
    "interpret_status",
    "crc16",
    "append_crc",
    "encode_command",
    "decode_response",
    "PHASE_CONVERSION",
    "RSSI_SOURCE",
]
