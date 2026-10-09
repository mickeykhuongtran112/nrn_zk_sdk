"""Public typed values; words are 16 bits, tag data remains lossless bytes."""

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Generic, TypeVar
from .errors import OperationError, ValidationError

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
