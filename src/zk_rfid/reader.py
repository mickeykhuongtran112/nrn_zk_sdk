"""Native async ZK public API. Construction/import never opens a device."""

from __future__ import annotations

import asyncio
import math
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import TYPE_CHECKING, TypeVar

from .capabilities import ReaderCapabilities
from .commands import Request
from .commands import (
    antenna,
    buffer,
    diagnostics,
    extended,
    inventory,
    io_control,
    power,
    reader_config,
    reader_info,
    rf_config,
    tag_access,
)
from .dispatcher import Dispatcher
from .errors import (
    RequestTimeout,
    ExchangeError,
    ProtocolError,
    StateError,
    ValidationError,
    UnverifiedFeature,
)
from .models import (
    BufferCounts,
    GPIOState,
    ReaderInfo,
    Region,
    WorkingModeConfig,
    WritePower,
    CommandResult,
    Confirmation,
    InventoryConfig,
    InventoryData,
    InventoryMode,
    InventoryOutcome,
    MemoryBank,
    Outcome,
    QueryParameters,
    ReaderState,
    RealTimeConfig,
    ScanParameters,
    TagMask,
    TagTarget,
    TIDParameters,
    WorkingMode,
    boolean,
)
from .protocol.status import interpret_status
from .transports.base import AsyncTransport

if TYPE_CHECKING:
    from .inventory_session import InventorySession

T = TypeVar("T")


class ZKReader:
    def __init__(
        self, transport: AsyncTransport, *, address=0, capabilities=None, timeout=3.0, on_event=None
    ):
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValidationError("timeout must be finite positive seconds")
        self.capabilities = capabilities or ReaderCapabilities()
        self.dispatcher = Dispatcher(transport, address=address, on_event=on_event)
        self.timeout = timeout
        self.state = ReaderState.DISCONNECTED
        self._operation_lock = asyncio.Lock()
        self._active_deadline = None
        self._session = None
        self.last_result: CommandResult | None = None
        self._working_mode = None  # Unknown until queried; do not claim a cached mode.
        self.dispatcher.on_fault = self._on_fault

    @property
    def state(self) -> ReaderState:
        """Host lifecycle state; IDLE alone does not prove a saved real-time mode is off."""
        return self._state

    @state.setter
    def state(self, value: ReaderState) -> None:
        previous = getattr(self, "_state", None)
        self._state = value
        if previous != value:
            self.dispatcher.trace.emit(
                "state", detail=f"{previous.value if previous else 'new'} -> {value.value}"
            )

    @property
    def address(self) -> int:
        """Current wire address; changes only after an acknowledged address update."""
        return self.dispatcher.address

    @property
    def is_inventory_running(self) -> bool:
        """Whether this host owns an active or transitioning inventory session."""
        return self.state in (ReaderState.STARTING, ReaderState.INVENTORYING, ReaderState.STOPPING)

    def get_capabilities(self) -> ReaderCapabilities:
        """Return declared capabilities and their evidence; no hardware probing."""
        return self.capabilities

    def _timeout(self, value=None, *, scan_time_100ms=None):
        chosen = self.timeout if value is None else value
        if (
            isinstance(chosen, bool)
            or not isinstance(chosen, (int, float))
            or not math.isfinite(chosen)
            or chosen <= 0
        ):
            raise ValidationError("timeout must be finite positive seconds")
        if value is None and scan_time_100ms is not None:
            chosen = max(chosen, scan_time_100ms * 0.1 + 0.25)
        return chosen

    @asynccontextmanager
    async def _operation(self, deadline=None):
        end = asyncio.get_running_loop().time() + self.timeout if deadline is None else deadline
        try:
            async with asyncio.timeout_at(end):
                await self._operation_lock.acquire()
        except TimeoutError as error:
            raise RequestTimeout(
                "Deadline expired before acquiring reader operation lock", transmitted=False
            ) from error
        self._active_deadline = end
        try:
            yield
        finally:
            self._active_deadline = None
            self._operation_lock.release()

    def _on_fault(self, error):
        self.state = ReaderState.UNKNOWN
        if self._session is not None:
            self._session._fault(error)

    async def open(self, *, recover: bool = False) -> "ZKReader":
        """Open transport and start the single RX task; recover requires a known clean boundary."""
        already_open = self.dispatcher.opened
        await self.dispatcher.open(recover=recover)
        if not already_open:
            self.state = ReaderState.IDLE
            self._working_mode = None
        return self

    async def close(self) -> None:
        """Stop owned inventory, close transport and join background tasks."""
        session = self._session
        try:
            if self._session is not None and self.dispatcher.fault is None:
                await self._session.stop()
            elif self.dispatcher.pending_command == 0x01 and self.dispatcher.fault is None:
                await self.stop_inventory()
        finally:
            if self._session is not None:
                self._session._fault(StateError("Reader closed"))
            await self.dispatcher.close()
            if session is not None and session._task is not None:
                if not session._task.done():
                    session._task.cancel()
                await asyncio.gather(session._task, return_exceptions=True)
            self._session = None
            self.state = ReaderState.DISCONNECTED

    async def __aenter__(self):
        return await self.open()

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def _guard(self, command, internal=False):
        if self.state is ReaderState.DISCONNECTED:
            raise StateError("Open reader first")
        if self.state is ReaderState.UNKNOWN:
            raise StateError("Reader state unknown; resynchronization is required")
        if not internal and self.is_inventory_running:
            if (
                self._session
                and self._session.mode is InventoryMode.REAL_TIME
                and command in (0x21, 0x77)
            ):
                return
            raise StateError("Stop inventory before changing reader/tag configuration")
        if self._working_mode in (WorkingMode.REAL_TIME, WorkingMode.TRIGGER) and command not in (
            0x21,
            0x76,
            0x77,
        ):
            raise StateError("Real-time firmware accepts only info, working-mode set/get")

    async def _execute(
        self, request: Request[T], *, deadline=None, internal=False, locked=False
    ) -> CommandResult[T]:
        if not locked:
            async with self._operation(deadline):
                return await self._execute(
                    request, deadline=deadline, internal=internal, locked=True
                )
        self._guard(request.command, internal)
        deadline = self._active_deadline if deadline is None else deadline
        try:
            frames = await self.dispatcher.exchange(
                request.command, request.data, timeout=self.timeout, deadline=deadline
            )
        except asyncio.CancelledError:
            self.last_result = CommandResult(
                Outcome.UNKNOWN,
                command=request.command,
                confirmation=Confirmation.TRANSMITTED,
                diagnostics=("Cancelled; operation may continue",),
            )
            raise
        except ExchangeError as error:
            result = CommandResult(
                Outcome.UNKNOWN if error.transmitted else Outcome.FAILURE,
                command=request.command,
                confirmation=Confirmation.TRANSMITTED if error.transmitted else Confirmation.NONE,
                diagnostics=(str(error),),
            )
        else:
            frame = frames[-1]
            status = interpret_status(frame.command, frame.status, frame.data)
            decoded, outcome, messages = None, status.outcome, ()
            if status.outcome is Outcome.SUCCESS:
                try:
                    decoded = request.decode(frame.data)
                except ProtocolError as error:
                    outcome = Outcome.UNKNOWN if request.mutating else Outcome.FAILURE
                    messages = (str(error),)
            else:
                messages = (status.name,)
            result = CommandResult(
                outcome,
                decoded,
                request.command,
                frame.status,
                status.tag_error,
                frame.data,
                Confirmation.ACKNOWLEDGED,
                messages,
            )
        self.last_result = result
        self.dispatcher.trace.emit(
            "result",
            exchange_id=self.dispatcher._exchange_sequence
            if result.confirmation is not Confirmation.NONE
            else None,
            command=result.command,
            status=result.status,
            detail=f"{result.outcome.value}; {result.confirmation.value}; {'; '.join(result.diagnostics)}",
        )
        return result

    async def get_reader_info(self) -> CommandResult[ReaderInfo]:
        """Read native reader identity, RF configuration and antenna-check state (0x21)."""
        result = await self._execute(reader_info.get_reader_info())
        if result.ok:
            result = replace(result, data=replace(result.data, address=self.address))
            self.last_result = result
        return result

    async def get_serial_number(self) -> CommandResult[bytes]:
        """Read the four-byte reader serial number (0x4C)."""
        return await self._execute(reader_info.get_serial_number())

    async def get_power(self) -> CommandResult[tuple[int, ...]]:
        """Read one integer dBm value per declared antenna (0x94)."""
        return await self._execute(power.get_power(ports=self.capabilities.antenna_ports))

    async def set_power(
        self, power_dbm: int | tuple[int, ...], *, persist: bool = False
    ) -> CommandResult[None]:
        """Set 0..30 dBm globally or per antenna; volatile unless persist=True (0x2F)."""
        return await self._execute(
            power.set_power(power_dbm, ports=self.capabilities.antenna_ports, persist=persist)
        )

    async def get_write_power(self) -> CommandResult[WritePower]:
        """Get write power. Returns native status and confirmation."""
        return await self._execute(power.get_write_power())

    async def set_write_power(self, power_dbm: int | None) -> CommandResult[None]:
        """Set separate write power in dBm, or None to disable it (0x79)."""
        return await self._execute(power.set_write_power(power_dbm))

    async def get_write_retries(self) -> CommandResult[int]:
        """Get write retries. Returns native status and confirmation."""
        return await self._execute(power.write_retries())

    async def set_write_retries(self, count: int) -> CommandResult[int]:
        """Set the module retry count 0..7; the host never retries writes (0x7B)."""
        return await self._execute(power.write_retries(count))

    async def set_antennas(self, mask: int, *, persist: bool = False) -> CommandResult[None]:
        """Select antenna mask with bit0=port1; volatile unless persist=True (0x3F)."""
        return await self._execute(
            antenna.set_antennas(mask, ports=self.capabilities.antenna_ports, persist=persist)
        )

    async def get_antennas(self) -> CommandResult[int]:
        """Get the native antenna mask; the 16-port getter remains unverified."""
        if self.capabilities.antenna_ports > 8:
            raise UnverifiedFeature("Reader-info antenna byte does not specify full 16-port mask")
        result = await self.get_reader_info()
        return replace(result, data=result.data.antenna_raw if result.ok else None)

    async def set_antenna_check(self, enabled: bool) -> CommandResult[None]:
        """Set antenna check. Returns native status and confirmation."""
        return await self._execute(antenna.set_antenna_check(enabled))

    async def get_antenna_check(self) -> CommandResult[bool]:
        """Get antenna check. Returns native status and confirmation."""
        result = await self.get_reader_info()
        return replace(result, data=result.data.antenna_check if result.ok else None)

    async def set_address(self, address: int) -> CommandResult[None]:
        """Change reader address after receiving the ACK at the original address (0x24)."""
        request = reader_config.set_address(address)
        async with self._operation():
            result = await self._execute(request, locked=True)
            if result.ok:
                self.dispatcher.address = address  # ACK uses original address.
            return result

    async def set_baudrate(self, baudrate: int) -> CommandResult[None]:
        """Receive ACK at the old baud, then switch the transport baud (0x28)."""
        request = reader_config.set_baudrate(baudrate)
        setter = getattr(self.dispatcher.transport, "set_baudrate", None)
        if setter is None:
            raise ValidationError(
                "Transport must implement async set_baudrate to switch both endpoints"
            )
        async with self._operation():
            result = await self._execute(request, locked=True)
            if result.ok:
                try:
                    await setter(baudrate)  # ACK is received at the old baud.
                except BaseException:
                    self.dispatcher._fail(
                        StateError("Module baud changed but transport update failed")
                    )
                    raise
            return result

    async def set_inventory_time(self, scan_time_100ms: int) -> CommandResult[None]:
        """Set native scan time in 100 ms units: 0 or 3..255 (0x25)."""
        return await self._execute(reader_config.set_scan_time(scan_time_100ms))

    async def set_interface(self, interface: str) -> CommandResult[None]:
        """Select usb or uart (0x6A); effective after a module power cycle."""
        return await self._execute(reader_config.set_interface(interface))

    async def get_region(self) -> CommandResult[Region]:
        """Get region. Returns native status and confirmation."""
        return await self._execute(rf_config.get_region())

    async def set_region(
        self, region: Region, *, persist: bool = False, legacy: bool = False
    ) -> CommandResult[None]:
        """Set native region and channel indices; no NATION region-ID conversion (0x22)."""
        return await self._execute(rf_config.set_region(region, persist=persist, legacy=legacy))

    async def get_profile(self, *, extended_format: bool = True) -> CommandResult[int]:
        """Read native RF profile ID, including the 16-bit Ex10 format (0x7F)."""
        return await self._execute(rf_config.profile(extended=extended_format))

    async def set_profile(
        self, profile_id: int, *, persist: bool = False, extended_format: bool = True
    ) -> CommandResult[int]:
        """Set native RF profile ID; no inferred equivalence with NATION profiles (0x7F)."""
        return await self._execute(
            rf_config.profile(profile_id, persist=persist, extended=extended_format)
        )

    async def get_drm(self) -> CommandResult[bool]:
        """Get drm. Returns native status and confirmation."""
        return await self._execute(rf_config.drm())

    async def set_drm(self, enabled: bool) -> CommandResult[bool]:
        """Set drm. Returns native status and confirmation."""
        return await self._execute(rf_config.drm(enabled))

    async def set_buzzer(self, enabled: bool) -> CommandResult[None]:
        """Set buzzer. Returns native status and confirmation."""
        return await self._execute(io_control.set_buzzer(enabled))

    async def pulse_indicator(
        self, active_50ms: int, silent_50ms: int, count: int
    ) -> CommandResult[None]:
        """Pulse LED/buzzer using 50 ms active/silent units (0x33)."""
        return await self._execute(io_control.indicator(active_50ms, silent_50ms, count))

    async def get_gpio(self) -> CommandResult[GPIOState]:
        """Read input and output bits in the documented GPIO layout (0x47)."""
        self.capabilities.require("gpio")
        return await self._execute(io_control.get_gpio())

    async def set_gpio(self, output1: bool, output2: bool) -> CommandResult[None]:
        """Set the two documented GPO outputs (0x46)."""
        self.capabilities.require("gpio")
        return await self._execute(io_control.set_gpio(output1, output2))

    async def get_temperature(self) -> CommandResult[int]:
        """Read signed integer Celsius using the native sign byte (0x92)."""
        self.capabilities.require("temperature")
        return await self._execute(diagnostics.get_temperature())

    async def measure_return_loss(self, frequency_khz: int, antenna: int = 1) -> CommandResult[int]:
        """Measure return loss at a documented grid frequency in kHz (0x91)."""
        return await self._execute(
            diagnostics.measure_return_loss(
                frequency_khz, antenna, ports=self.capabilities.antenna_ports
            )
        )

    async def get_return_loss_threshold(self) -> CommandResult[int]:
        """Get return loss threshold. Returns native status and confirmation."""
        return await self._execute(diagnostics.return_loss_threshold())

    async def set_return_loss_threshold(self, threshold_db: int) -> CommandResult[int]:
        """Set return loss threshold. Returns native status and confirmation."""
        return await self._execute(diagnostics.return_loss_threshold(threshold_db))

    async def get_config(
        self, number: int, *, decoded: bool = True
    ) -> CommandResult[
        ScanParameters | QueryParameters | TIDParameters | TagMask | tuple[int, ...] | bool | bytes
    ]:
        """Read an Ex10 CFG value; decoded=False preserves the exact native bytes (0xEB)."""
        self.capabilities.require("ex10")
        return await self._execute(extended.get_config(number, decoded=decoded))

    async def set_config(
        self, number: int, data: bytes, *, persist: bool = False
    ) -> CommandResult[None]:
        """Validate and set Ex10 CFG; ambiguous CFG25/29 require an explicit dialect (0xEA)."""
        self.capabilities.require("ex10")
        length = (
            self.capabilities.cfg25_length
            if number == 25
            else self.capabilities.cfg29_length
            if number == 29
            else None
        )
        return await self._execute(
            extended.set_config(number, data, persist=persist, confirmed_length=length)
        )

    async def get_scan_parameters(self) -> CommandResult[ScanParameters]:
        """Get scan parameters. Returns native status and confirmation."""
        return await self.get_config(7)

    async def set_scan_parameters(
        self, parameters: ScanParameters, *, persist: bool = False
    ) -> CommandResult[None]:
        """Set scan parameters. Returns native status and confirmation."""
        return await self.set_config(7, extended.encode_scan(parameters), persist=persist)

    async def get_tag_focus(self) -> CommandResult[bool]:
        """Get tag focus. Returns native status and confirmation."""
        return await self.get_config(8)

    async def set_tag_focus(self, enabled: bool, *, persist: bool = False) -> CommandResult[None]:
        """Set tag focus. Returns native status and confirmation."""
        return await self.set_config(8, bytes((boolean(enabled, "enabled"),)), persist=persist)

    async def get_query_parameters(self) -> CommandResult[QueryParameters]:
        """Get query parameters. Returns native status and confirmation."""
        return await self.get_config(9)

    async def set_query_parameters(
        self, parameters: QueryParameters, *, persist: bool = False
    ) -> CommandResult[None]:
        """Set query parameters. Returns native status and confirmation."""
        return await self.set_config(9, extended.encode_query(parameters), persist=persist)

    async def get_tid_parameters(self) -> CommandResult[TIDParameters]:
        """Get tid parameters. Returns native status and confirmation."""
        return await self.get_config(10)

    async def set_tid_parameters(
        self, parameters: TIDParameters, *, persist: bool = False
    ) -> CommandResult[None]:
        """Set tid parameters. Returns native status and confirmation."""
        return await self.set_config(10, extended.encode_tid(parameters), persist=persist)

    async def get_inventory_mask(self) -> CommandResult[TagMask]:
        """Get inventory mask. Returns native status and confirmation."""
        return await self.get_config(11)

    async def set_inventory_mask(
        self, mask: TagMask | None, *, persist: bool = False
    ) -> CommandResult[None]:
        """Set inventory mask. Returns native status and confirmation."""
        data = (mask or TagMask(MemoryBank.EPC, 32, 0, b"")).encode()
        return await self.set_config(11, data, persist=persist)

    async def get_custom_profiles(self) -> CommandResult[tuple[int, ...]]:
        """Get custom profiles. Returns native status and confirmation."""
        return await self.get_config(31)

    async def set_custom_profiles(
        self, profile_ids: tuple[int, int, int], *, persist: bool = False
    ) -> CommandResult[None]:
        """Set custom profiles. Returns native status and confirmation."""
        return await self.set_config(31, extended.encode_profiles(profile_ids), persist=persist)

    async def set_real_time_config(self, config: RealTimeConfig) -> CommandResult[None]:
        """Persist the dedicated 0x75 real-time settings; separate from Scenario CFG."""
        self.capabilities.require("realtime")
        return await self._execute(reader_config.set_real_time(config))

    async def get_working_mode(self) -> CommandResult[WorkingModeConfig]:
        """Read the 0x77 mode and fixed-width saved real-time configuration."""
        result = await self._execute(reader_config.get_working_mode())
        if result.ok:
            self._working_mode = result.data.mode
        return result

    async def set_working_mode(self, mode: WorkingMode) -> CommandResult[None]:
        """Persistent mode setting. For managed 0xEE delivery use start_inventory()."""
        request = reader_config.set_working_mode(mode)
        async with self._operation():
            result = await self._execute(request, locked=True)
            if result.ok:
                self._working_mode = WorkingMode(mode)
            return result

    async def get_heartbeat_interval(self) -> CommandResult[int]:
        """Get heartbeat interval. Returns native status and confirmation."""
        return await self._execute(reader_config.heartbeat())

    async def set_heartbeat_interval(self, interval_30s: int) -> CommandResult[int]:
        """Set heartbeat interval in 30 second units, with 0 disabling it (0x78)."""
        return await self._execute(reader_config.heartbeat(interval_30s))

    async def get_buffer_length(self) -> CommandResult[int]:
        """Get buffer length. Returns native status and confirmation."""
        return await self._execute(buffer.get_buffer_length())

    async def set_buffer_length(self, max_bytes: int) -> CommandResult[None]:
        """Set maximum stored EPC/TID length to 16 or 62 bytes; clears the buffer (0x70)."""
        return await self._execute(buffer.set_buffer_length(max_bytes))

    async def get_buffer_count(self) -> CommandResult[int]:
        """Get buffer count. Returns native status and confirmation."""
        return await self._execute(buffer.get_buffer_count())

    async def clear_buffer(self) -> CommandResult[None]:
        """Clear the reader tag buffer (0x73)."""
        return await self._execute(buffer.clear_buffer())

    async def inventory_to_buffer(
        self, config: InventoryConfig = InventoryConfig(), *, timeout: float | None = None
    ) -> CommandResult[BufferCounts]:
        """Run buffered inventory and return counts; this changes reader buffer contents (0x18)."""
        request = inventory.build_inventory(
            config, ports=self.capabilities.antenna_ports, buffered=True
        )
        deadline = asyncio.get_running_loop().time() + self._timeout(
            timeout, scan_time_100ms=config.scan_time_100ms
        )
        return await self._execute(replace(request, decode=buffer.decode_counts), deadline=deadline)

    async def read_buffer(
        self, *, data_kind: InventoryData = InventoryData.EPC, timeout: float | None = None
    ) -> InventoryOutcome:
        """Collect all 0x72 frames; preserve partial reports and enforce one overall deadline."""
        from .inventory_session import collect_buffer

        return await collect_buffer(self, data_kind, self._timeout(timeout))

    async def inventory_once(
        self, config: InventoryConfig = InventoryConfig(), *, timeout: float | None = None
    ) -> InventoryOutcome:
        """Run one Answer/Mix round, preserving reports on partial completion or timeout."""
        from .inventory_session import collect_answer

        return await collect_answer(
            self, config, timeout=self._timeout(timeout, scan_time_100ms=config.scan_time_100ms)
        )

    async def inventory_single(self, *, timeout: float | None = None) -> InventoryOutcome:
        """Run native single-tag inventory (0x0F)."""
        from .inventory_session import collect_answer

        return await collect_answer(
            self, InventoryConfig(), timeout=self._timeout(timeout), request=Request(0x0F)
        )

    async def inventory_matching_epc(
        self,
        data: bytes,
        bit_length: int,
        *,
        bit_offset: int = 0,
        exclude: bool = False,
        timeout: float | None = None,
    ) -> InventoryOutcome:
        """Run native EPC-bit-match inventory with explicit bit offset and length (0x1A)."""
        from .inventory_session import collect_answer

        request = inventory.inventory_epc(data, bit_length, bit_offset, exclude=exclude)
        return await collect_answer(
            self, InventoryConfig(), timeout=self._timeout(timeout), request=request
        )

    async def start_inventory(
        self,
        mode: InventoryMode = InventoryMode.SCENARIO,
        *,
        config: InventoryConfig = InventoryConfig(),
        queue_size: int = 1024,
        trigger: bool = False,
    ) -> InventorySession:
        """Start a managed async report iterator; stop explicitly or use its context manager."""
        from .inventory_session import InventorySession

        session = InventorySession(self, mode, config, queue_size=queue_size, trigger=trigger)
        await session.start()
        return session

    async def stop_inventory(self) -> InventoryOutcome:
        """Stop by mode-specific semantics; 0x93 has no ACK of its own."""
        if self._session is not None:
            return await self._session.stop()
        if self.dispatcher.pending_command == 0x01:
            # collect_answer owns the request; wait for its normal completion.
            await self.dispatcher.interrupt_answer()
            task = getattr(self, "_answer_done", None)
            if task is not None:
                return await asyncio.shield(task)
        if self.is_inventory_running:
            raise StateError("This inventory opcode has no asynchronous stop command")
        return InventoryOutcome(termination_reason="already_idle")

    async def read_memory(
        self,
        bank: MemoryBank,
        word_address: int,
        word_count: int,
        *,
        target: TagTarget | None = None,
        access_password: bytes = tag_access.ZERO_PASSWORD,
        extended_format: bool | None = None,
    ) -> CommandResult[bytes]:
        """Read 1..120 16-bit words; choose extended address format automatically when needed."""
        return await self._execute(
            tag_access.read_memory(
                bank,
                word_address,
                word_count,
                target=target,
                access_password=access_password,
                extended=extended_format,
            )
        )

    def _verification_target(self, target, bank, address, count, verification_target):
        chosen = verification_target or target
        if chosen is None:
            raise ValidationError("Read-back verification requires an explicit target")
        if verification_target is None and target is not None:
            if target.epc is not None and bank == MemoryBank.EPC:
                raise ValidationError(
                    "Provide a post-write verification_target when changing EPC/PC"
                )
            if target.mask is not None and target.mask.bank == bank:
                lo, hi = target.mask.bit_address, target.mask.bit_address + target.mask.bit_length
                if max(lo, address * 16) < min(hi, (address + count) * 16):
                    raise ValidationError(
                        "Write changes target mask; supply a post-write verification_target"
                    )
        return chosen

    async def write_memory(
        self,
        bank: MemoryBank,
        word_address: int,
        data: bytes,
        *,
        target: TagTarget | None = None,
        access_password: bytes = tag_access.ZERO_PASSWORD,
        extended_format: bool | None = None,
        verify: bool = False,
        verification_target: TagTarget | None = None,
        verification_password: bytes | None = None,
        timeout: float | None = None,
    ) -> CommandResult[bytes | None]:
        """Write 1..32 words once, optionally verify using a stable post-write target."""
        request = tag_access.write_memory(
            bank,
            word_address,
            data,
            target=target,
            access_password=access_password,
            extended=extended_format,
        )
        boolean(verify, "verify")
        read_request = None
        if verify:
            selected = self._verification_target(
                target, bank, word_address, len(data) // 2, verification_target
            )
            if (
                bank == MemoryBank.RESERVED
                and word_address < 4
                and word_address + len(data) // 2 > 2
                and verification_password is None
            ):
                raise ValidationError("Access-password write requires verification_password")
            pwd = access_password if verification_password is None else verification_password
            read_request = tag_access.read_memory(
                bank, word_address, len(data) // 2, target=selected, access_password=pwd
            )
        deadline = asyncio.get_running_loop().time() + self._timeout(timeout)
        async with self._operation(deadline):
            written = await self._execute(request, deadline=deadline, locked=True)
            if not written.ok or not verify:
                return written
            try:
                checked = await self._execute(read_request, deadline=deadline, locked=True)
            except asyncio.CancelledError:
                self._cancelled_write((written,))
                raise
            result = self._verified_write(written, checked, data)
            self.last_result = result
            return result

    def _verified_write(self, written, checked, expected):
        if checked.ok and checked.data == expected:
            return replace(
                written,
                data=expected,
                confirmation=Confirmation.READ_BACK,
                steps=(written, checked),
            )
        return replace(
            written,
            outcome=Outcome.PARTIAL,
            data=checked.data,
            steps=(written, checked),
            diagnostics=("Write acknowledged but read-back failed or mismatched",)
            + checked.diagnostics,
        )

    def _cancelled_write(self, confirmed_steps):
        """Retain acknowledged writes when cancellation interrupts later verification."""
        interrupted = self.last_result
        self.last_result = replace(
            confirmed_steps[-1],
            outcome=Outcome.PARTIAL,
            steps=(*confirmed_steps, interrupted),
            diagnostics=("Write acknowledged; host cancelled before verification completed",),
        )

    async def write_epc(
        self,
        epc: bytes,
        *,
        target: TagTarget,
        access_password: bytes = tag_access.ZERO_PASSWORD,
        verify: bool = True,
        verification_target: TagTarget | None = None,
        timeout: float | None = None,
    ) -> CommandResult[bytes | None]:
        """Read PC, preserve non-length bits, then one targeted PC+EPC write."""
        tag_access.pc_with_epc_length(b"\0\0", epc)
        tag_access.selection(target)
        if target is None:
            raise ValidationError(
                "Targeted write_epc requires a target; use write_epc_single for 0x04"
            )
        boolean(verify, "verify")
        selected = (
            self._verification_target(
                target, MemoryBank.EPC, 1, 1 + len(epc) // 2, verification_target
            )
            if verify
            else None
        )
        deadline = asyncio.get_running_loop().time() + self._timeout(timeout)
        async with self._operation(deadline):
            pc = await self._execute(
                tag_access.read_memory(
                    MemoryBank.EPC, 1, 1, target=target, access_password=access_password
                ),
                deadline=deadline,
                locked=True,
            )
            if not pc.ok:
                return pc
            desired = tag_access.pc_with_epc_length(pc.data, epc) + epc
            try:
                written = await self._execute(
                    tag_access.write_memory(
                        MemoryBank.EPC, 1, desired, target=target, access_password=access_password
                    ),
                    deadline=deadline,
                    locked=True,
                )
            except asyncio.CancelledError:
                self.last_result = replace(self.last_result, steps=(pc, self.last_result))
                raise
            if not written.ok or not verify:
                self.last_result = replace(written, steps=(pc, written))
                return self.last_result
            try:
                checked = await self._execute(
                    tag_access.read_memory(
                        MemoryBank.EPC,
                        1,
                        len(desired) // 2,
                        target=selected,
                        access_password=access_password,
                    ),
                    deadline=deadline,
                    locked=True,
                )
            except asyncio.CancelledError:
                self._cancelled_write((pc, written))
                raise
            result = replace(
                self._verified_write(written, checked, desired), steps=(pc, written, checked)
            )
            self.last_result = result
            return result

    async def write_epc_single(
        self, epc: bytes, *, access_password: bytes = tag_access.ZERO_PASSWORD
    ) -> CommandResult[None]:
        """Native 0x04. Requires exactly one tag physically in the RF field."""
        return await self._execute(
            tag_access.write_epc_single(epc, access_password=access_password)
        )

    async def set_access_password(
        self,
        new_password: bytes,
        *,
        target: TagTarget,
        access_password: bytes = tag_access.ZERO_PASSWORD,
        verify: bool = True,
    ) -> CommandResult[bytes | None]:
        """Write the 32-bit Access password, then verify using the new password if requested."""
        tag_access.password(new_password)
        return await self.write_memory(
            MemoryBank.RESERVED,
            2,
            new_password,
            target=target,
            access_password=access_password,
            verify=verify,
            verification_password=new_password,
        )

    async def set_kill_password(
        self,
        new_password: bytes,
        *,
        target: TagTarget,
        access_password: bytes = tag_access.ZERO_PASSWORD,
        verify: bool = True,
    ) -> CommandResult[bytes | None]:
        """Write the 32-bit Kill password; does not execute Kill or Lock."""
        tag_access.password(new_password)
        return await self.write_memory(
            MemoryBank.RESERVED,
            0,
            new_password,
            target=target,
            access_password=access_password,
            verify=verify,
        )

    async def lock_tag(
        self,
        lock_target: int,
        protection: int,
        *,
        target: TagTarget,
        access_password: bytes = tag_access.ZERO_PASSWORD,
    ) -> CommandResult[None]:
        """Apply native Gen2 protection to a specified target; permanent states are irreversible."""
        return await self._execute(
            tag_access.lock_tag(
                lock_target, protection, target=target, access_password=access_password
            )
        )

    async def kill_tag(self, kill_password: bytes, *, target: TagTarget) -> CommandResult[None]:
        """Execute irreversible Gen2 Kill on an explicit target with a nonzero 32-bit password."""
        return await self._execute(tag_access.kill_tag(kill_password, target=target))

    async def block_write(
        self,
        bank: MemoryBank,
        word_address: int,
        data: bytes,
        *,
        target: TagTarget | None = None,
        access_password: bytes = tag_access.ZERO_PASSWORD,
    ) -> CommandResult[None]:
        """Use native BlockWrite within its independent frame budget; tag support is required."""
        return await self._execute(
            tag_access.write_memory(
                bank, word_address, data, target=target, access_password=access_password, block=True
            )
        )

    async def block_erase(
        self,
        bank: MemoryBank,
        word_address: int,
        word_count: int,
        *,
        target: TagTarget | None = None,
        access_password: bytes = tag_access.ZERO_PASSWORD,
    ) -> CommandResult[None]:
        """Erase 1..120 words using native BlockErase; tag support is required."""
        return await self._execute(
            tag_access.block_erase(
                bank, word_address, word_count, target=target, access_password=access_password
            )
        )

    async def select_tag(
        self,
        mask: TagMask,
        *,
        antenna_mask: int = 1,
        select_target: int = 4,
        action: int = 0,
        truncate: bool = False,
    ) -> CommandResult[None]:
        """Apply native Gen2 Select using a bit-addressed mask, target, action and antenna mask."""
        return await self._execute(
            tag_access.select_tag(
                mask,
                antenna_mask=antenna_mask,
                ports=self.capabilities.antenna_ports,
                select_target=select_target,
                action=action,
                truncate=truncate,
            )
        )
