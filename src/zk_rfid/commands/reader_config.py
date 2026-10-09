"""Reader control and real-time mode, V2.25 sections 8.4.3-5/15/22-25."""

from ._common import Request, ack, exact
from ..errors import ProtocolError, ValidationError
from ..models import RealTimeConfig, TagMask, WorkingMode, WorkingModeConfig, boolean, integer

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
