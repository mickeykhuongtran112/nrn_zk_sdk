"""Gen2 access builders; one RF command per write, no automatic retry/split."""

from ._common import Request, ack, exact
from ..errors import ValidationError
from ..models import MemoryBank, TagTarget, TagMask, boolean, integer, octets

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
