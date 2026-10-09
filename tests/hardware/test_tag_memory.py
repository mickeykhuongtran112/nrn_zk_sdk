"""Scratch-tag checks; no write without explicit environment opt-in."""

import os
import pytest
from zk_rfid import MemoryBank, Confirmation

pytestmark = [pytest.mark.hardware, pytest.mark.asyncio]


async def test_read_tid(hardware_reader, hardware_target):
    data = (
        await hardware_reader.read_memory(MemoryBank.TID, 0, 2, target=hardware_target)
    ).require_success()
    assert len(data) == 4


async def test_scratch_user_roundtrip(hardware_reader, hardware_target):
    if os.environ.get("ZK_ALLOW_TAG_WRITE") != "1":
        pytest.skip("Writing requires ZK_ALLOW_TAG_WRITE=1 and a disposable, writable tag")
    address = int(os.environ.get("ZK_USER_WORD_ADDRESS", "0"))
    old = (
        await hardware_reader.read_memory(MemoryBank.USER, address, 1, target=hardware_target)
    ).require_success()
    test = bytes(v ^ 0x5A for v in old)
    changed = False
    try:
        changed = True
        result = await hardware_reader.write_memory(
            MemoryBank.USER, address, test, target=hardware_target, verify=True
        )
        assert result.confirmation is Confirmation.READ_BACK
    finally:
        if changed and not hardware_reader.dispatcher.fault:
            restored = await hardware_reader.write_memory(
                MemoryBank.USER, address, old, target=hardware_target, verify=True
            )
            assert restored.confirmation is Confirmation.READ_BACK
        # A timed-out write is NOT retried; manually inspect tag after resynchronization.
