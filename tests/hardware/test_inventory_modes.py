"""Inventory emits RF and clears/uses buffers; manually select these tests."""

import pytest
from zk_rfid import InventoryConfig, InventoryMode, Outcome

pytestmark = [pytest.mark.hardware, pytest.mark.asyncio]


async def test_answer_round(hardware_reader):
    result = await hardware_reader.inventory_once(InventoryConfig(scan_time_100ms=3))
    assert result.outcome in (Outcome.SUCCESS, Outcome.PARTIAL)
    assert result.status in (1, 2, 4, 0xFB)


async def test_scenario_start_stop(hardware_reader):
    session = await hardware_reader.start_inventory(InventoryMode.SCENARIO)
    result = await session.stop()
    assert result.complete
