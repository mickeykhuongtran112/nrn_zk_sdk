"""Hardware is opened only after explicit -m hardware AND environment selection."""

import os

import pytest
import pytest_asyncio

from zk_rfid import MemoryBank, ReaderCapabilities, SerialTransport, TagMask, TagTarget, ZKReader


@pytest_asyncio.fixture
async def hardware_reader():
    port = os.environ.get("ZK_HARDWARE_PORT")
    if not port:
        pytest.skip("Set ZK_HARDWARE_PORT and explicitly select -m hardware")
    ports = int(os.environ.get("ZK_ANTENNA_PORTS", "1"))
    baud = int(os.environ.get("ZK_BAUDRATE", "57600"))
    async with ZKReader(
        SerialTransport(port, baud),
        timeout=5,
        capabilities=ReaderCapabilities(
            antenna_ports=ports,
            model=os.environ.get("ZK_MODEL"),
            firmware=os.environ.get("ZK_FIRMWARE"),
        ),
    ) as reader:
        yield reader


@pytest.fixture
def hardware_target():
    tid = os.environ.get("ZK_TEST_TID")
    if not tid:
        pytest.skip("Set the known scratch tag TID in ZK_TEST_TID")
    data = bytes.fromhex(tid)
    return TagTarget(mask=TagMask(MemoryBank.TID, 0, len(data) * 8, data))
