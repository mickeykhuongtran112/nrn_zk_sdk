"""Inventory lifecycle; only Dispatcher reads bytes from the transport."""

import asyncio
import math
from dataclasses import replace

from .commands import Request
from .commands import antenna, buffer, extended, inventory, reader_config, reader_info
from .commands._common import ack
from .errors import (
    ExchangeError,
    OperationError,
    ProtocolError,
    QueueOverflow,
    StateError,
    UnsupportedFeature,
    ValidationError,
)
from .models import (
    InventoryData,
    InventoryMode,
    InventoryOutcome,
    Outcome,
    QueryParameters,
    ReaderState,
    TagMask,
    TIDParameters,
    WorkingMode,
    integer,
)
from .protocol.status import interpret_status


def _outcome(reports, status, stats, diagnostics, *, reason=None, unknown=False, partial=False):
    failure = status is not None and status not in (1, 2, 4, 0x26, 0xFB)
    incomplete = unknown or partial or failure or status in (2, 4)
    outcome = (
        Outcome.PARTIAL
        if reports and incomplete
        else Outcome.UNKNOWN
        if unknown
        else Outcome.FAILURE
        if failure
        else Outcome.PARTIAL
        if incomplete
        else Outcome.SUCCESS
    )
    return InventoryOutcome(
        tuple(reports),
        reason
        or {
            1: "completed",
            2: "device_timeout",
            4: "buffer_full",
            0xFB: "no_tag",
            0x26: "statistics",
        }.get(status, "device_error"),
        outcome,
        status,
        not incomplete,
        stats,
        tuple(diagnostics),
        len(reports),
    )


async def collect_answer(reader, config, *, timeout, request=None, managed=False, on_report=None):
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValidationError("timeout must be finite positive seconds")
    request = request or inventory.build_inventory(config, ports=reader.capabilities.antenna_ports)
    inventory.validate_inventory(config, reader.capabilities.antenna_ports)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    reports, messages = [], []
    statistics, final_status = None, None
    decoder = (
        inventory.MixDecoder(config, reader.capabilities.antenna_ports)
        if config.data is InventoryData.MIX
        else None
    )
    before_loss = reader.dispatcher.parser.diagnostics.discarded_bytes
    done = loop.create_future()
    result = None
    unknown = False

    def receive(frame):
        nonlocal statistics, final_status
        if frame.status == 0x26:
            statistics = inventory.decode_statistics(frame.data)
            if final_status is None:
                final_status = 0x26
        elif frame.status in (1, 2, 3, 4):
            decoded = (
                decoder.feed(frame.data, loop.time())
                if decoder
                else inventory.decode_answer(
                    frame.data,
                    config,
                    ports=reader.capabilities.antenna_ports,
                    received_at=loop.time(),
                )
            )
            if len(reports) + len(decoded) > 65536:
                raise QueueOverflow("Answer inventory exceeds 65536 reports")
            reports.extend(decoded)
            if on_report:
                for report in decoded:
                    on_report(report)
            if frame.status != 3:
                final_status = frame.status
        else:
            final_status = frame.status
            if frame.status != 0xFB:
                status = interpret_status(frame.command, frame.status, frame.data)
                messages.append(
                    status.name
                    + (f": tag_error={status.tag_error}" if status.tag_error is not None else "")
                )
            elif frame.data:
                raise ProtocolError("No-tag response unexpectedly contains data")

    def terminal(frame):
        if frame.status == 3:
            return False
        if config.statistics and frame.status in (1, 2, 4):
            return False
        return True

    async with reader._operation(deadline):
        reader._guard(request.command, internal=managed)
        reader.state = ReaderState.INVENTORYING
        reader._answer_done = done
        try:
            await reader.dispatcher.exchange(
                request.command,
                request.data,
                timeout=timeout,
                deadline=deadline,
                terminal=terminal,
                on_frame=receive,
            )
        except asyncio.CancelledError:
            unknown = True
            messages.append("Host cancelled; reader may still be inventorying")
            raise
        except ExchangeError as error:
            unknown = error.transmitted
            messages.append(str(error))
        finally:
            if decoder:
                remaining = decoder.flush()
                reports.extend(remaining)
                if on_report:
                    for report in remaining:
                        on_report(report)
                if decoder.missing_memory or decoder.orphan_memory:
                    messages.append(
                        f"Mix missing_memory={decoder.missing_memory}, orphan_memory={decoder.orphan_memory}"
                    )
            lost = reader.dispatcher.parser.diagnostics.discarded_bytes - before_loss
            if lost:
                messages.append(f"Parser discarded {lost} bytes")
            result = _outcome(
                reports,
                final_status,
                statistics,
                messages,
                reason="host_incomplete" if unknown else None,
                unknown=unknown,
                partial=bool(
                    lost or (decoder and (decoder.missing_memory or decoder.orphan_memory))
                ),
            )
            reader.state = (
                ReaderState.UNKNOWN
                if reader.dispatcher.fault
                else ReaderState.INVENTORYING
                if managed
                else ReaderState.IDLE
            )
            reader.last_inventory_outcome = result
            if not done.done():
                done.set_result(result)
            reader._answer_done = None
    return result


async def collect_buffer(reader, data_kind, timeout):
    deadline = asyncio.get_running_loop().time() + timeout
    reports, messages, status, unknown = [], [], None, False
    caps = reader.capabilities
    # Validate ambiguous hardware layout before sending.
    buffer.decode_buffer(
        b"\0",
        ports=caps.antenna_ports,
        data_kind=data_kind,
        antenna_bytes=caps.buffer_antenna_bytes,
    )

    def receive(frame):
        nonlocal status
        status = frame.status
        if status in (1, 3):
            reports.extend(
                buffer.decode_buffer(
                    frame.data,
                    ports=caps.antenna_ports,
                    data_kind=data_kind,
                    antenna_bytes=caps.buffer_antenna_bytes,
                )
            )
            if len(reports) > 65536:
                raise QueueOverflow("Reader buffer response exceeds 65536 reports")
        else:
            messages.append(interpret_status(frame.command, status, frame.data).name)

    async with reader._operation(deadline):
        reader._guard(0x72)
        before = reader.dispatcher.parser.diagnostics.discarded_bytes
        try:
            await reader.dispatcher.exchange(
                0x72,
                timeout=timeout,
                deadline=deadline,
                terminal=lambda f: f.status != 3,
                on_frame=receive,
            )
        except asyncio.CancelledError:
            reader.last_inventory_outcome = _outcome(
                reports, status, None, ["Host cancelled buffer read"], unknown=True
            )
            raise
        except ExchangeError as error:
            unknown = error.transmitted
            messages.append(str(error))
        lost = reader.dispatcher.parser.diagnostics.discarded_bytes - before
        if lost:
            messages.append(f"Parser discarded {lost} bytes")
    return _outcome(reports, status, None, messages, unknown=unknown, partial=bool(lost))


class InventorySession:
    """Async iterator of TagReport or Heartbeat with explicit stop and final outcome.

    Scenario applies volatile CFG9/10/11 and one antenna, verifies them, and
    restores snapshots after a confirmed stop. Real-time uses the already saved
    0x75 configuration; 0x76 start/stop changes persistent working mode.
    Stream outcome stores counters; the consumer owns delivered report storage.
    """

    def __init__(self, reader, mode, config, *, queue_size=1024, trigger=False):
        if not isinstance(mode, InventoryMode):
            raise ValidationError("mode must be InventoryMode")
        integer(queue_size, 1, 1000000, "queue_size")
        inventory.validate_inventory(
            replace(config, session=0) if mode is InventoryMode.SCENARIO else config,
            reader.capabilities.antenna_ports,
        )
        if mode is not InventoryMode.ANSWER and config.data not in (
            InventoryData.EPC,
            InventoryData.TID,
        ):
            raise UnsupportedFeature(
                "Scenario/Real-time do not have a verified FastID/Mix contract"
            )
        if mode is InventoryMode.SCENARIO:
            reader.capabilities.require("ex10")
            extended.encode_query(QueryParameters(config.q, config.session, config.phase))
            if config.statistics or config.special_strategy:
                raise UnsupportedFeature(
                    "Scenario does not use Answer statistics/special-strategy flags"
                )
        if mode is InventoryMode.REAL_TIME:
            reader.capabilities.require("realtime")
            if config.phase or config.statistics or config.special_strategy:
                raise UnsupportedFeature("Real-time 0xEE has no verified phase/statistics flags")
        self.reader, self.mode, self.config = reader, mode, config
        self.trigger = trigger
        self.queue = asyncio.Queue(maxsize=queue_size)
        self._finished = asyncio.Event()
        self._stopping = asyncio.Event()
        self._stop_lock = asyncio.Lock()
        self._task = None
        self._error = None
        self._snapshots = []
        self._started = False
        self._closed = False
        self._stop_ack = False
        self._tid_words = 0
        self._received = 0
        self._dropped = 0
        self._heartbeats = 0
        self._messages = []
        self._start_discarded = 0
        self.outcome: InventoryOutcome | None = None

    async def start(self):
        reader = self.reader
        async with reader._operation():
            reader._guard(
                0x50
                if self.mode is InventoryMode.SCENARIO
                else 0x76
                if self.mode is InventoryMode.REAL_TIME
                else 0x01
            )
            if reader._session is not None:
                raise StateError("An inventory session already owns this reader")
            reader._session = self
            reader.state = ReaderState.STARTING
            self._start_discarded = reader.dispatcher.parser.diagnostics.discarded_bytes
            if self.mode is InventoryMode.ANSWER:
                reader.state = ReaderState.INVENTORYING
                self._started = True
                self._task = asyncio.create_task(self._answer_loop(), name="zk-answer-session")
                return self
            reader.dispatcher.on_notification = self._notification
            try:
                if self.mode is InventoryMode.SCENARIO:
                    await self._prepare_scenario()
                    request = inventory.fast_start(self.config.target)
                else:
                    current = (
                        await reader._execute(
                            reader_config.get_working_mode(), internal=True, locked=True
                        )
                    ).require_success()
                    reader._working_mode = current.mode
                    self._tid_words = current.config.tid_word_count
                    expected = InventoryData.TID if self._tid_words else InventoryData.EPC
                    if self.config.data is not expected:
                        raise ValidationError(
                            "Real-time data kind differs from saved 0x75 configuration"
                        )
                    request = reader_config.set_working_mode(
                        WorkingMode.TRIGGER if self.trigger else WorkingMode.REAL_TIME
                    )
                # Mark before TX, because failure/timeout can leave RF running.
                self._started = True
                result = await reader._execute(request, internal=True, locked=True)
                result.require_success()
                if self.mode is InventoryMode.REAL_TIME:
                    reader._working_mode = (
                        WorkingMode.TRIGGER if self.trigger else WorkingMode.REAL_TIME
                    )
                reader.state = ReaderState.INVENTORYING
            except BaseException as error:
                self._error = error
                # If Start was rejected with a definitive response, RF did not start.
                definite_rejection = (
                    isinstance(error, OperationError) and error.result.outcome is Outcome.FAILURE
                )
                if not self._started or definite_rejection:
                    self._started = False
                    if reader.dispatcher.fault is None:
                        await self._restore()
                self._finished.set()
                reader._session = None
                reader.state = (
                    ReaderState.UNKNOWN
                    if self._started or reader.dispatcher.fault
                    else ReaderState.IDLE
                )
                raise
        return self

    async def _prepare_scenario(self):
        reader, cfg = self.reader, self.config
        self._tid_words = cfg.tid_word_count if cfg.data is InventoryData.TID else 0
        desired = [
            (9, extended.encode_query(QueryParameters(cfg.q, cfg.session, cfg.phase))),
            (10, extended.encode_tid(TIDParameters(cfg.tid_word_address, self._tid_words))),
            (11, (cfg.mask or TagMask(1, 32, 0, b"")).encode()),
        ]
        # Get all snapshots before making any change.
        snapshots = []
        for number, data in desired:
            old = (
                await reader._execute(
                    extended.get_config(number, decoded=False), internal=True, locked=True
                )
            ).require_success()
            snapshots.append((number, old, data))
        ports = reader.capabilities.antenna_ports
        old_ant = None
        if ports > 1:
            if ports > 8:
                raise UnsupportedFeature(
                    "Scenario auto-restore needs a verified 16-port antenna mask getter"
                )
            info = (
                await reader._execute(reader_info.get_reader_info(), internal=True, locked=True)
            ).require_success()
            old_ant = info.antenna_raw
            antenna.set_antennas(old_ant, ports=ports)  # Prevalidate restoration.
        for number, old, data in snapshots:
            if old == data:
                continue
            self._snapshots.append(Request(0xEA, bytes((1, number)) + old, ack, True))
            (
                await reader._execute(extended.set_config(number, data), internal=True, locked=True)
            ).require_success()
            checked = (
                await reader._execute(
                    extended.get_config(number, decoded=False), internal=True, locked=True
                )
            ).require_success()
            if checked != data:
                raise ProtocolError(f"CFG{number} read-back mismatch before start")
        if old_ant is not None and old_ant != 1 << (cfg.antenna - 1):
            self._snapshots.append(antenna.set_antennas(old_ant, ports=ports))
            (
                await reader._execute(
                    antenna.set_antennas(1 << (cfg.antenna - 1), ports=ports),
                    internal=True,
                    locked=True,
                )
            ).require_success()

    async def _restore(self):
        reader = self.reader
        errors = []
        while self._snapshots:
            request = self._snapshots.pop()
            try:
                result = await reader._execute(request, internal=True, locked=True)
                result.require_success()
                if request.command == 0xEA:
                    actual = (
                        await reader._execute(
                            extended.get_config(request.data[1], decoded=False),
                            internal=True,
                            locked=True,
                        )
                    ).require_success()
                    if actual != request.data[2:]:
                        raise ProtocolError("Configuration restoration read-back mismatch")
                elif request.command == 0x3F:
                    actual = (
                        await reader._execute(
                            reader_info.get_reader_info(), internal=True, locked=True
                        )
                    ).require_success()
                    expected = (
                        request.data[0] & 15
                        if len(request.data) == 1
                        else int.from_bytes(request.data[1:], "big")
                    )
                    if actual.antenna_raw != expected:
                        raise ProtocolError("Antenna restoration read-back mismatch")
            except Exception as error:
                errors.append(str(error))
                if reader.dispatcher.fault:
                    break
        if errors:
            error = ProtocolError("Restoration failed: " + "; ".join(errors))
            self._messages.append(str(error))
            reader.dispatcher._fail(error)
            self._error = self._error or error

    def _notification(self, frame):
        try:
            pending = self.reader.dispatcher._pending
            ack_in_same_chunk = (
                pending
                and pending.command in (0x51, 0x76)
                and pending.future.done()
                and self._stopping.is_set()
            )
            if self._stop_ack or ack_in_same_chunk:
                # Do not attribute late frames to the next inventory generation.
                raise ProtocolError("Tag/heartbeat after stop ACK; stream boundary is unverified")
            if frame.status == 0x28:
                value = inventory.decode_heartbeat(
                    frame.data, ports=self.reader.capabilities.antenna_ports
                )
                self._heartbeats += 1
            elif frame.status == 0:
                value = inventory.decode_stream(
                    frame.data,
                    ports=self.reader.capabilities.antenna_ports,
                    tid_words=self._tid_words,
                    received_at=asyncio.get_running_loop().time(),
                    scenario=self.mode is InventoryMode.SCENARIO,
                )
                self._received += 1
            else:
                raise ProtocolError(f"Unexpected streaming status 0x{frame.status:02X}")
            self._enqueue(value)
        except Exception as error:
            self._fault(error)
            if isinstance(error, ProtocolError) and not isinstance(error, QueueOverflow):
                self.reader.dispatcher._fail(error)

    def _enqueue(self, value):
        try:
            self.queue.put_nowait(value)
        except asyncio.QueueFull:
            self._dropped += 1
            self._fault(
                QueueOverflow(
                    "Inventory queue overflow; stop and increase queue/consumer throughput"
                )
            )

    def _fault(self, error):
        self._error = self._error or error
        self._finished.set()

    async def _answer_loop(self):
        def receive(report):
            self._received += 1
            self._enqueue(report)

        try:
            while not self._stopping.is_set() and not self._error:
                result = await collect_answer(
                    self.reader,
                    self.config,
                    timeout=self.reader._timeout(scan_time_100ms=self.config.scan_time_100ms),
                    managed=True,
                    on_report=receive,
                )
                if not result.complete:
                    self._messages.extend(result.diagnostics or (result.termination_reason,))
                if self.reader.dispatcher.fault:
                    break
                await asyncio.sleep(0)  # Yield even for immediate fake/in-memory responses.
        except Exception as error:
            self._fault(error)
        finally:
            self._finished.set()

    async def stop(self) -> InventoryOutcome:
        async with self._stop_lock:
            if self._closed:
                return self.outcome
            self._stopping.set()
            reader = self.reader
            reader.state = (
                ReaderState.STOPPING if not reader.dispatcher.fault else ReaderState.UNKNOWN
            )
            if self.mode is InventoryMode.ANSWER:
                if reader.dispatcher.pending_command == 0x01 and not reader.dispatcher.fault:
                    await reader.dispatcher.interrupt_answer()
                if self._task:
                    await self._task  # Mix has no 0x93; its bounded round must finish.
                self._stop_ack = not bool(reader.dispatcher.fault)
            else:
                async with reader._operation():
                    if not reader.dispatcher.fault and self._started:
                        request = (
                            inventory.fast_stop()
                            if self.mode is InventoryMode.SCENARIO
                            else reader_config.set_working_mode(WorkingMode.ANSWER)
                        )
                        result = await reader._execute(request, internal=True, locked=True)
                        if result.ok and not reader.dispatcher.fault:
                            self._stop_ack = True
                            if self.mode is InventoryMode.REAL_TIME:
                                reader._working_mode = WorkingMode.ANSWER
                            await self._restore()
                        else:
                            self._fault(OperationError(result))
            lost = reader.dispatcher.parser.diagnostics.discarded_bytes - self._start_discarded
            if lost:
                self._messages.append(f"Parser discarded {lost} bytes")
            if self._error:
                self._messages.append(str(self._error))
            uncertain = not self._stop_ack or bool(reader.dispatcher.fault)
            partial = bool(self._messages or self._dropped)
            self.outcome = InventoryOutcome(
                termination_reason="stop_unconfirmed" if uncertain else "stopped",
                outcome=Outcome.UNKNOWN
                if uncertain
                else Outcome.PARTIAL
                if partial
                else Outcome.SUCCESS,
                complete=not uncertain and not partial,
                diagnostics=tuple(self._messages),
                received_count=self._received,
                dropped_count=self._dropped,
            )
            self._closed = True
            self._finished.set()
            reader._session = None
            reader.state = ReaderState.UNKNOWN if uncertain else ReaderState.IDLE
            # Retain the callback after stop to detect illegal late 0xEE frames.
            return self.outcome

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.queue.empty():
            return self.queue.get_nowait()
        if self._finished.is_set():
            if self._error:
                raise self._error
            raise StopAsyncIteration
        get_task = asyncio.create_task(self.queue.get())
        end_task = asyncio.create_task(self._finished.wait())
        try:
            done, _ = await asyncio.wait((get_task, end_task), return_when=asyncio.FIRST_COMPLETED)
            if get_task in done:
                return get_task.result()
            if self._error:
                raise self._error
            raise StopAsyncIteration
        finally:
            for task in (get_task, end_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(get_task, end_task, return_exceptions=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()
