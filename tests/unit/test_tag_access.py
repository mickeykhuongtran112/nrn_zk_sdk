import pytest
from zk_rfid import MemoryBank, TagMask, TagTarget, ValidationError
from zk_rfid.commands import tag_access as t

MASK = TagTarget(mask=TagMask(MemoryBank.TID, 32, 16, b"\xe2\x80"))


def test_documented_read_write_layouts():
    assert t.read_memory(3, 0x1234, 2, target=MASK).data.hex() == "ff031234020000000002002010e280"
    assert t.read_memory(3, 0x1234, 2, target=MASK).command == 0x15
    request = t.write_memory(3, 0, b"\x12\x34", target=MASK)
    assert request.command == 3
    assert request.data.hex() == "01ff030012340000000002002010e280"
    assert t.write_memory(3, 300, b"\0\x01", target=MASK).command == 0x16


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(word_count=0),
        dict(word_count=121),
        dict(word_address=-1),
        dict(word_address=65535, word_count=2),
        dict(bank=4),
        dict(access_password=b"\0" * 3),
        dict(extended=False, word_address=256),
    ],
)
def test_invalid_read_before_io(kwargs):
    args = dict(bank=3, word_address=0, word_count=1)
    args.update(kwargs)
    with pytest.raises(ValidationError):
        t.read_memory(**args)


@pytest.mark.parametrize("data", [b"", b"\0", bytes(66)])
def test_write_word_limit(data):
    with pytest.raises(ValidationError):
        t.write_memory(3, 0, data)


def test_block_limit_is_frame_budget_not_generic_write():
    assert t.write_memory(3, 0, bytes(100), block=True).command == 0x10
    with pytest.raises(ValidationError):
        t.write_memory(3, 256, b"\0\0", block=True)
    with pytest.raises(ValidationError):
        t.write_memory(3, 0, bytes(242), target=MASK, block=True)


def test_target_and_mask_validation():
    with pytest.raises(ValidationError):
        TagTarget(epc=b"\0\0", mask=MASK.mask)
    with pytest.raises(ValidationError):
        TagMask(2, 0, 3, b"\xe1")
    with pytest.raises(ValidationError):
        TagMask(2, 16383, 2, b"\xc0")
    assert TagMask(2, 0, 3, b"\xe0").encode() == b"\x02\0\0\x03\xe0"


def test_lock_kill_erase_select_layout():
    assert t.lock_tag(4, 2, target=MASK).data.hex() == "ff04020000000002002010e280"
    assert t.kill_tag(b"\x12\x34\x56\x78", target=MASK).data.hex() == "ff1234567802002010e280"
    with pytest.raises(ValidationError):
        t.kill_tag(bytes(4), target=MASK)
    with pytest.raises(ValidationError):
        t.block_erase(1, 0, 1)
    assert t.select_tag(MASK.mask, antenna_mask=0x8001, ports=16).data[:4] == bytes.fromhex(
        "80010400"
    )


def test_pc_preservation():
    old = bytes.fromhex("37A5")
    changed = t.pc_with_epc_length(old, bytes(8))
    assert int.from_bytes(changed, "big") >> 11 == 4
    assert int.from_bytes(changed, "big") & 0x7FF == int.from_bytes(old, "big") & 0x7FF
