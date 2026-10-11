"""Optional asynchronous NATION-style facade over the native ZK reader.

Partial power/antenna updates use the reader's internal transaction lock and native builders;
keep this module paired with the SDK revision shipped in the same checkout.
Approved GReaderTool choices are applied only by explicit configuration calls.
"""

import asyncio
import inspect
from dataclasses import replace

from zk_rfid import (
    InventoryConfig,
    InventoryData,
    InventoryMode,
    Confirmation,
    Outcome,
    Region,
    SDK_NAME,
    SDK_VERSION,
    TagReport,
    TagTarget,
    UnsupportedFeature,
    ValidationError,
    boolean,
    get_power,
    get_reader_info,
    integer,
    set_antennas,
    set_power,
    profile,
    get_region,
    set_region,
    set_custom_region,
)

from .values import RFMapping, hex_epc, power_dict, tag_dict, unsupported
from .policy import baseband_choice, region_choice

# ==============================================================================
# NATION async API adapter
# ==============================================================================

# Familiar NATION operation names with an explicit async ZK result contract.
#
# Not a drop-in for blocking/threaded nrn.py. Never imports the reference driver,
# builds NATION frames, or substitutes numeric RF identifiers.


class NationAdapter:
    def __init__(self, reader):
        self.reader = reader
        self.inventory_config = InventoryConfig()

    async def open(self):
        return await self.reader.open()

    async def close(self):
        return await self.reader.close()

    def get_sdk_info(self):

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
                get_power(ports=reader.capabilities.antenna_ports), locked=True
            )
            if not before.ok:
                return before
            desired = list(before.data)
            for port, dbm in antenna_powers.items():
                desired[port - 1] = dbm
            result = await reader._execute(
                set_power(
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
        reader = self.reader
        request = set_antennas(antenna_mask, ports=reader.capabilities.antenna_ports, persist=True)
        async with reader._operation():
            return await self._verified_write(
                request, get_reader_info(), lambda info: info.antenna_raw == antenna_mask
            )

    async def query_enabled_ant_mask(self):
        return await self.reader.get_antennas()

    async def _change_antenna(self, ant_id, enabled, save):
        reader = self.reader
        ports = reader.capabilities.antenna_ports
        integer(ant_id, 1, ports, "ant_id")
        if ports > 8:
            raise UnsupportedFeature("Full antenna readback not verified for 16 ports")
        async with reader._operation():
            before = await reader._execute(get_reader_info(), locked=True)
            if not before.ok:
                return before
            mask = before.data.antenna_raw
            mask = mask | (1 << (ant_id - 1)) if enabled else mask & ~(1 << (ant_id - 1))
            result = await self._verified_write(
                set_antennas(mask, ports=ports, persist=save),
                get_reader_info(),
                lambda info: info.antenna_raw == mask,
            )
            return replace(result, steps=(before, *result.steps))

    async def enable_ant(self, ant_id: int, save=True):
        if save is not True:
            raise ValidationError("NATION antenna configuration always uses SAVE")
        return await self._change_antenna(ant_id, True, save)

    async def disable_ant(self, ant_id: int, save=True):
        if save is not True:
            raise ValidationError("NATION antenna configuration always uses SAVE")
        return await self._change_antenna(ant_id, False, save)

    def is_inventory_running(self):
        return self.reader.is_inventory_running

    async def start_inventory_with_mode(
        self, antenna_ids: list[int], *, mode=InventoryMode.SCENARIO, config=None, include_tid=False
    ):
        """EPC uses Scenario; include_tid selects repeating Answer FastID rounds.

        Save checkbox settings separately with save_antenna_mask(); Start never
        writes nonvolatile settings. FastID may return EPC without TID on other tags.
        """
        boolean(include_tid, "include_tid")
        config = config if config is not None else self.inventory_config
        mask = self.build_antenna_mask(antenna_ids)
        if include_tid:
            config, mode = replace(config, data=InventoryData.FAST_ID), InventoryMode.ANSWER
        if mode is InventoryMode.SCENARIO:
            return await self.reader.start_inventory(
                mode, config=replace(config, antenna=antenna_ids[0]), antenna_mask=mask
            )
        if mode is InventoryMode.ANSWER:
            return await self.reader.start_inventory(
                mode,
                config=replace(config, antenna=antenna_ids[0]),
                antenna_sequence=tuple(antenna_ids),
            )
        if mask & (mask - 1):
            raise UnsupportedFeature("Multiple antennas require Scenario inventory")
        return await self.reader.start_inventory(
            mode, config=replace(config, antenna=antenna_ids[0])
        )

    async def run_inventory(
        self,
        antenna_ids: list[int],
        callback,
        *,
        duration: float,
        mode=InventoryMode.SCENARIO,
        config=None,
        include_tid=False,
    ):
        """Run for duration seconds; callback errors propagate after Stop cleanup.

        Callbacks run in the consumer task, outside RX. Only expiration of this
        method's duration is normal completion; callback timeouts remain errors.
        """
        if not callable(callback) or not isinstance(duration, (int, float)) or duration <= 0:
            raise ValidationError("Provide callback and a positive duration in seconds")
        session = await self.start_inventory_with_mode(
            antenna_ids, mode=mode, config=config, include_tid=include_tid
        )
        deadline = asyncio.timeout(duration)
        consumer_timeout = None
        try:
            async with deadline:
                try:
                    async for report in session:
                        if not isinstance(report, TagReport):
                            continue
                        result = callback(tag_dict(report))
                        if inspect.isawaitable(result):
                            await result
                except TimeoutError as error:
                    # Preserve consumer errors even if a callback translates the
                    # duration's cancellation into its own TimeoutError.
                    consumer_timeout = error
                    raise
        except TimeoutError as error:
            if error is consumer_timeout or not deadline.expired():
                raise
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

    async def _verified_write(self, request, read, matches):
        """Caller owns the operation lock. Never turn a failed save into success."""
        written = await self.reader._execute(request, locked=True)
        if not written.ok:
            return written
        actual = await self.reader._execute(read, locked=True)
        if not actual.ok:
            return replace(actual, steps=(written, actual))
        if not matches(actual.data):
            return replace(
                actual,
                outcome=Outcome.PARTIAL,
                confirmation=Confirmation.ACKNOWLEDGED,
                diagnostics=actual.diagnostics + ("Configuration read-back mismatch",),
                steps=(written, actual),
            )
        return replace(actual, confirmation=Confirmation.READ_BACK, steps=(written, actual))

    async def configure_baseband(self, speed, q_value, session, inventory_flag, *, persist=False):
        """Apply approved speed mapping; stage Q/Session/Target for subsequent Start.

        Speed 255 keeps the current profile; it does not emulate NATION Auto.
        Only the RF profile has device persistence; run settings live in this adapter.
        """
        row = baseband_choice(speed)
        integer(q_value, 0, 15, "q_value")
        integer(session, 0, 3, "session")
        integer(inventory_flag, 0, 1, "inventory_flag (A=0, B=1)")
        boolean(persist, "persist")
        async with self.reader._operation():
            if row["zk_profile_id"] is None:
                result = await self.reader._execute(profile(), locked=True)
            else:
                result = await self._verified_write(
                    profile(row["zk_profile_id"], persist=persist),
                    profile(),
                    lambda value: value == row["zk_profile_id"],
                )
            if result.ok:
                self.inventory_config = replace(
                    self.inventory_config, q=q_value, session=session, target=inventory_flag
                )
            return replace(result, diagnostics=result.diagnostics + (row["difference"],))

    async def query_baseband_profile(self):
        """Native profile read-back plus application-owned Q/Session/Target."""
        result = await self.reader.get_profile()
        if not result.ok:
            return result
        return replace(
            result,
            data={
                "zk_profile_id": result.data,
                "baseband_source": "greader-0.39",
                "q": self.inventory_config.q,
                "session": self.inventory_config.session,
                "target": self.inventory_config.target,
                "run_settings_source": "application",
            },
        )

    async def set_rf_band(self, band_code: int, persist=False):
        """Apply the approved full demo center list, or reject before I/O."""
        region = region_choice(band_code)
        request = (set_region if isinstance(region, Region) else set_custom_region)(
            region, persist=persist
        )
        async with self.reader._operation():
            return await self._verified_write(request, get_region(), lambda value: value == region)

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
