"""Read-only configuration checks on an explicitly selected module."""

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.asyncio]


async def test_info_serial_and_power(hardware_reader):
    info = (await hardware_reader.get_reader_info()).require_success()
    serial = (await hardware_reader.get_serial_number()).require_success()
    powers = (await hardware_reader.get_power()).require_success()
    assert info.protocol_flags & 2
    assert len(serial) == 4 and len(powers) == hardware_reader.capabilities.antenna_ports


async def test_region_and_profile(hardware_reader):
    region = (await hardware_reader.get_region()).require_success()
    profile = (await hardware_reader.get_profile()).require_success()
    assert region.min_channel <= region.max_channel
    assert 0 <= profile <= 65535
