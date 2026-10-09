"""Answer/FastID/TID/Mix codecs, V2.25 8.2.1/14/21/22 and 8.4.41."""

from dataclasses import replace
from ._common import Request, ack, exact
from .antenna import decode_antenna
from .tag_access import password
from ..errors import ProtocolError, ValidationError, UnverifiedFeature
from ..measurements import _rssi_fields
from ..models import (
    Heartbeat,
    InventoryConfig,
    InventoryData,
    InventoryStatistics,
    TagMask,
    TagReport,
    boolean,
    integer,
)


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
        from ..measurements import PHASE_CONVERSION, phase_to_degrees, phase_to_radians

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
