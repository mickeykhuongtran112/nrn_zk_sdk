"""Typed Ex10 CFG7/8/9/10/11/25/29/31; conflicting lengths are explicit."""

from ._common import Request, ack, exact, raw, switch
from ..errors import ProtocolError, ValidationError, UnverifiedFeature
from ..models import QueryParameters, ScanParameters, TIDParameters, TagMask, boolean, integer

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
