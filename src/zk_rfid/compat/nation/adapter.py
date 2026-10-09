"""Familiar NATION operation names with an explicit async ZK result contract.

Not a drop-in for blocking/threaded nrn.py. Never imports the reference driver,
builds NATION frames, or substitutes numeric RF identifiers.
"""

import asyncio
import inspect
from dataclasses import replace
from ...commands import antenna, power, reader_info
from ...models import InventoryConfig, InventoryMode, TagTarget, boolean, integer
from ...errors import UnsupportedFeature, ValidationError
from .mapping import RFMapping, hex_epc, power_dict, tag_dict, unsupported


class NationAdapter:
    def __init__(self, reader):
        self.reader = reader

    async def open(self):
        return await self.reader.open()

    async def close(self):
        return await self.reader.close()

    def get_sdk_info(self):
        from ... import SDK_NAME, SDK_VERSION

        return {"name": SDK_NAME, "version": SDK_VERSION, "adapter": "NATION async operations"}

    async def Query_Reader_Information(self):
        return await self.reader.get_reader_info()

    async def query_rfid_ability(self):
        return self.reader.get_capabilities()

    async def query_reader_power(self):
        result = await self.reader.get_power()
        return replace(result, data=power_dict(result.data) if result.ok else None)

    async def configure_reader_power(
        self, antenna_powers: dict[int, int], persistence: bool = False
    ):
        if not isinstance(antenna_powers, dict) or not antenna_powers:
            raise ValidationError("antenna_powers must be a nonempty dictionary")
        boolean(persistence, "persistence")
        reader = self.reader
        for port, dbm in antenna_powers.items():
            integer(port, 1, reader.capabilities.antenna_ports, "antenna")
            integer(dbm, 0, 30, "ZK power_dbm")
        async with reader._operation():
            before = await reader._execute(
                power.get_power(ports=reader.capabilities.antenna_ports), locked=True
            )
            if not before.ok:
                return before
            desired = list(before.data)
            for port, dbm in antenna_powers.items():
                desired[port - 1] = dbm
            result = await reader._execute(
                power.set_power(
                    tuple(desired), ports=reader.capabilities.antenna_ports, persist=persistence
                ),
                locked=True,
            )
            return replace(result, steps=(before, result))

    def build_antenna_mask(self, antenna_ids: list[int]) -> int:
        if not antenna_ids or len(set(antenna_ids)) != len(antenna_ids):
            raise ValidationError("Antenna IDs must be nonempty and unique")
        for port in antenna_ids:
            integer(port, 1, self.reader.capabilities.antenna_ports, "antenna")
        return sum(1 << (p - 1) for p in antenna_ids)

    async def save_antenna_mask(self, antenna_mask: int):
        return await self.reader.set_antennas(antenna_mask, persist=True)

    async def query_enabled_ant_mask(self):
        return await self.reader.get_antennas()

    async def _change_antenna(self, ant_id, enabled, save):
        reader = self.reader
        ports = reader.capabilities.antenna_ports
        integer(ant_id, 1, ports, "ant_id")
        if ports > 8:
            raise UnsupportedFeature("Full antenna readback not verified for 16 ports")
        async with reader._operation():
            before = await reader._execute(reader_info.get_reader_info(), locked=True)
            if not before.ok:
                return before
            mask = before.data.antenna_raw
            mask = mask | (1 << (ant_id - 1)) if enabled else mask & ~(1 << (ant_id - 1))
            result = await reader._execute(
                antenna.set_antennas(mask, ports=ports, persist=save), locked=True
            )
            return replace(result, steps=(before, result))

    async def enable_ant(self, ant_id: int, save=False):
        return await self._change_antenna(ant_id, True, save)

    async def disable_ant(self, ant_id: int, save=False):
        return await self._change_antenna(ant_id, False, save)

    def is_inventory_running(self):
        return self.reader.is_inventory_running

    async def start_inventory_with_mode(
        self, antenna_ids: list[int], *, mode=InventoryMode.SCENARIO, config=InventoryConfig()
    ):
        mask = self.build_antenna_mask(antenna_ids)
        if mask & (mask - 1):
            raise UnsupportedFeature("This adapter stream contract selects one antenna per session")
        return await self.reader.start_inventory(
            mode, config=replace(config, antenna=antenna_ids[0])
        )

    async def run_inventory(
        self, antenna_ids: list[int], callback, *, duration: float, mode=InventoryMode.SCENARIO
    ):
        """Callbacks run in the consumer task, outside RX; callback failure stops RF."""
        if not callable(callback) or not isinstance(duration, (int, float)) or duration <= 0:
            raise ValidationError("Provide callback and a positive duration in seconds")
        session = await self.start_inventory_with_mode(antenna_ids, mode=mode)
        try:
            async with asyncio.timeout(duration):
                async for report in session:
                    from ...models import TagReport

                    if not isinstance(report, TagReport):
                        continue
                    result = callback(tag_dict(report))
                    if inspect.isawaitable(result):
                        await result
        except TimeoutError:
            pass
        finally:
            outcome = await session.stop()
        return outcome

    async def stop_inventory(self):
        return await self.reader.stop_inventory()

    async def write_epc_to_target_auto(
        self, target_tag_epc: str, new_epc_hex: str, *, access_pwd=0, timeout=3.0, verify=True
    ):
        old, new = hex_epc(target_tag_epc), hex_epc(new_epc_hex)
        if len(old) > 30 or len(new) > 30:
            raise UnsupportedFeature(
                "Adapter exact EPC target supports 1..15 words; use native stable TID mask for longer EPC"
            )
        integer(access_pwd, 0, 0xFFFFFFFF, "access_pwd")
        return await self.reader.write_epc(
            new,
            target=TagTarget(epc=old),
            access_password=access_pwd.to_bytes(4, "big"),
            verify=verify,
            verification_target=TagTarget(epc=new),
            timeout=timeout,
        )

    async def select_profile(
        self, profile_id: int, *, mapping: RFMapping | None = None, persist=False
    ):
        if mapping is None:
            unsupported("rf_profile")
        return await self.reader.set_profile(mapping.require(profile_id), persist=persist)

    async def get_profile(self):
        """Result contains a native ZK ID; no NATION equivalence is implied."""
        return await self.reader.get_profile()

    async def query_rf_band(self):
        """Result contains native Region fields, not NATION band codes."""
        return await self.reader.get_region()

    async def set_rf_band(self, band_code: int, persist=True):
        unsupported("rf_band")

    async def set_beeper(self, mode: int):
        integer(mode, 0, 2, "mode")
        if mode == 1:
            raise UnsupportedFeature("NATION beep-after-inventory is not ZK beep-on-every-tag")
        return await self.reader.set_buzzer(mode == 2)

    async def get_beeper(self):
        unsupported("beeper_query")

    async def set_filter_settings(self, repeated_time_ms=0, rssi_threshold=0):
        unsupported("native_filter")

    async def get_session(self):
        result = await self.reader.get_query_parameters()
        return replace(result, data=result.data.session if result.ok else None)
