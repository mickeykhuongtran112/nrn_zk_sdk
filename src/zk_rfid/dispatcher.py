"""One RX task and one ordinary request. No transaction IDs, no unsafe retry."""

import asyncio
import math
from dataclasses import dataclass, field
from typing import Callable

from .errors import ExchangeError, ProtocolError, RequestTimeout, StateError, TransportError
from .events import TraceEmitter
from .models import integer
from .protocol.frame import ResponseFrame, encode_command
from .protocol.parser import FrameParser
from .transports.base import AsyncTransport


@dataclass
class _Pending:
    command: int
    future: asyncio.Future
    terminal: Callable[[ResponseFrame], bool]
    on_frame: Callable[[ResponseFrame], None] | None
    frames: list[ResponseFrame] = field(default_factory=list)
    transmitted: bool = False
    exchange_id: int = 0


class Dispatcher:
    """Timeout/cancellation after TX poisons this connection until explicit recovery.

    open(recover=True) is an assertion by the caller that the old device operation
    has ended and stale bytes cannot arrive (e.g. physical reset/reconnection).
    Closing a port alone does not stop reader RF.
    """

    def __init__(self, transport: AsyncTransport, *, address=0, max_frames=4096, on_event=None):
        self.transport = transport
        self.address = integer(address, 0, 255, "address")
        self.max_frames = integer(max_frames, 1, 1000000, "max_frames")
        self.parser = FrameParser()
        self._lock = asyncio.Lock()
        self._tx_lock = asyncio.Lock()
        self._pending: _Pending | None = None
        self._rx_task: asyncio.Task | None = None
        self.opened = False
        self.fault: Exception | None = None
        self.on_notification: Callable[[ResponseFrame], None] | None = None
        self.on_fault: Callable[[Exception], None] | None = None
        self.unsolicited: list[ResponseFrame] = []
        self.last_exchange_error: ExchangeError | None = None
        self.trace = TraceEmitter(on_event)
        self._exchange_sequence = 0

    @property
    def pending_command(self) -> int | None:
        return self._pending.command if self._pending else None

    async def open(self, *, recover=False) -> None:
        if self.opened:
            if self.fault:
                raise StateError("Close and establish a clean device boundary before recovery")
            return
        if self.fault and not recover:
            raise StateError(
                "Unknown prior command state; explicit open(recover=True) requires resynchronization"
            )
        try:
            await self.transport.open()
        except BaseException:
            await self.transport.close()
            raise
        self.parser.reset()
        self.fault = None
        self.opened = True
        self._rx_task = asyncio.create_task(self._receive(), name="zk-rfid-rx")
        self.trace.emit("connected", address=self.address)

    async def close(self) -> None:
        self.opened = False
        if self._pending:
            self._fail(TransportError("Connection closed while a command was pending"))
        task, self._rx_task = self._rx_task, None
        if task:
            task.cancel()
        try:
            await self.transport.close()
        finally:
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self.trace.emit("disconnected", address=self.address)

    def _check(self):
        if not self.opened:
            raise StateError("Reader is closed")
        if self.fault is not None:
            raise StateError(f"Connection is desynchronized: {self.fault}")

    def _fail(self, error: Exception):
        if self.fault is None:
            self.fault = error
            self.trace.emit("fault", detail=f"{type(error).__name__}: {error}")
        p = self._pending
        if p and not p.future.done():
            wrapped = ExchangeError(str(error), frames=p.frames, transmitted=p.transmitted)
            p.future.set_exception(wrapped)
        if self.on_fault is not None:
            self.on_fault(error)

    async def _write_all(self, wire: bytes, *, exchange_id=None) -> None:
        async with self._tx_lock:
            offset = 0
            while offset < len(wire):
                count = await self.transport.write(wire[offset:])
                if (
                    isinstance(count, bool)
                    or not isinstance(count, int)
                    or not 0 < count <= len(wire) - offset
                ):
                    raise TransportError("Invalid/zero transport write count")
                self.trace.emit(
                    "tx",
                    exchange_id=exchange_id,
                    command=wire[2],
                    address=wire[1],
                    raw=wire[offset : offset + count],
                    detail="transport-accepted bytes",
                )
                offset += count

    async def exchange(
        self,
        command: int,
        data: bytes = b"",
        *,
        timeout=3.0,
        deadline: float | None = None,
        terminal=None,
        on_frame=None,
    ) -> tuple[ResponseFrame, ...]:
        wire = encode_command(self.address, command, data)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (float, int))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be finite positive seconds")
        loop = asyncio.get_running_loop()
        end = loop.time() + timeout if deadline is None else deadline
        if not math.isfinite(end) or end <= loop.time():
            raise RequestTimeout("Deadline expired before TX", transmitted=False)
        p = None
        try:
            async with asyncio.timeout_at(end):
                async with self._lock:
                    self._check()
                    if loop.time() >= end:
                        raise RequestTimeout(
                            "Deadline expired while waiting for request lock", transmitted=False
                        )
                    self._exchange_sequence += 1
                    p = _Pending(
                        command,
                        loop.create_future(),
                        terminal or (lambda f: True),
                        on_frame,
                        exchange_id=self._exchange_sequence,
                    )
                    self._pending = p  # Register before the first TX byte.
                    self.trace.emit(
                        "request",
                        exchange_id=p.exchange_id,
                        command=command,
                        address=self.address,
                        raw=wire,
                    )
                    try:
                        p.transmitted = True  # Even a failed/short write may reach the module.
                        await self._write_all(wire, exchange_id=p.exchange_id)
                        return await asyncio.shield(p.future)
                    finally:
                        if self._pending is p:
                            self._pending = None
        except asyncio.CancelledError:
            if p and p.transmitted:
                error = ExchangeError(
                    "Host cancelled; device operation may continue",
                    frames=p.frames,
                    transmitted=True,
                )
                self.last_exchange_error = error
                self.trace.emit(
                    "cancelled", exchange_id=p.exchange_id, command=command, detail=str(error)
                )
                self._fail(error)
            raise
        except TimeoutError as cause:
            error = RequestTimeout(
                "Host deadline expired",
                frames=p.frames if p else (),
                transmitted=p.transmitted if p else False,
            )
            self.last_exchange_error = error
            self.trace.emit(
                "timeout",
                exchange_id=p.exchange_id if p else None,
                command=command,
                detail=str(error),
            )
            if p and p.transmitted:
                self._fail(error)
            raise error from cause
        except (StateError, ValueError):
            raise
        except Exception as cause:
            error = (
                cause
                if isinstance(cause, ExchangeError)
                else ExchangeError(
                    str(cause),
                    frames=p.frames if p else (),
                    transmitted=p.transmitted if p else False,
                )
            )
            self.last_exchange_error = error
            if p and p.transmitted:
                self._fail(error)
            raise error from cause
        finally:
            if p and not p.future.done():
                p.future.cancel()
            elif p and not p.future.cancelled():
                p.future.exception()  # Retrieve errors when TX itself failed before awaiting RX.

    async def interrupt_answer(self, *, timeout=1.0) -> bool:
        """Send 0x93 only while 0x01 is pending; it has no independent ACK."""
        self._check()
        p = self._pending
        if p is None or p.command != 0x01 or p.future.done():
            return False
        try:
            async with asyncio.timeout(timeout):
                # Do not acquire the ordinary request lock: inventory owns it.
                self.trace.emit(
                    "interrupt",
                    exchange_id=p.exchange_id,
                    command=0x93,
                    detail="Interrupt pending 0x01; no independent ACK",
                )
                await self._write_all(encode_command(self.address, 0x93), exchange_id=p.exchange_id)
        except BaseException as cause:
            self._fail(TransportError("Unable to transmit inventory interrupt"))
            raise cause
        return True

    async def _receive(self):
        try:
            while self.opened:
                chunk = await self.transport.read(4096)
                if not isinstance(chunk, bytes):
                    raise TransportError("Transport.read must return bytes")
                if not chunk:
                    raise TransportError("Transport EOF")
                self.trace.emit("rx", raw=chunk, detail="transport read chunk")
                discarded_before = self.parser.diagnostics.discarded_bytes
                parsed = self.parser.feed(chunk)
                if self.parser.diagnostics.discarded_bytes != discarded_before:
                    self.trace.emit(
                        "parser_loss",
                        detail=str(self.parser.diagnostics.discarded_bytes - discarded_before),
                    )
                for frame in parsed:
                    active = self._pending
                    self.trace.emit(
                        "frame",
                        exchange_id=active.exchange_id
                        if active and frame.command != 0xEE
                        else None,
                        command=frame.command,
                        address=frame.address,
                        status=frame.status,
                        raw=frame.raw,
                    )
                    if self.address != 255 and frame.address != self.address:
                        self._unexpected(frame, poison=False)
                        continue
                    if frame.command == 0xEE:
                        if self.on_notification is not None:
                            self.on_notification(frame)
                        else:
                            self._unexpected(frame, poison=False)
                        continue
                    p = self._pending
                    if p is None or p.future.done():
                        self._unexpected(frame, poison=True)
                        continue
                    if frame.command != p.command and not (
                        frame.command == 0 and frame.status == 0xFE
                    ):
                        self._unexpected(frame, poison=True)
                        continue
                    if self.address == 255:
                        self.address = frame.address  # Single point-to-point reader only.
                    if len(p.frames) >= self.max_frames:
                        raise ProtocolError("Exchange frame limit exceeded")
                    p.frames.append(frame)
                    if p.on_frame:
                        p.on_frame(frame)
                    if p.terminal(frame):
                        p.future.set_result(tuple(p.frames))
                        self.trace.emit(
                            "response_complete",
                            exchange_id=p.exchange_id,
                            command=p.command,
                            status=frame.status,
                        )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._fail(error)

    def _unexpected(self, frame, *, poison):
        self.trace.emit(
            "unexpected",
            command=frame.command,
            status=frame.status,
            address=frame.address,
            raw=frame.raw,
            detail="connection invalidated" if poison else "not matched",
        )
        self.parser.diagnostics.unexpected_frames += 1
        self.unsolicited.append(frame)
        if len(self.unsolicited) > 32:
            del self.unsolicited[0]
        if poison:
            self._fail(
                ProtocolError(f"Unexpected response 0x{frame.command:02X}; stale reply possible")
            )
