"""Optional CPython transport; pyserial is imported only by open()."""

import asyncio
from ..errors import TransportError
from ..models import integer


class SerialTransport:
    def __init__(self, port: str, baudrate=57600, *, read_timeout=0.05, write_timeout=1.0):
        if not isinstance(port, str) or not port:
            raise ValueError("Explicit serial port is required")
        self.port = port
        self.baudrate = integer(baudrate, 1, 4000000, "baudrate")
        if not 0 < read_timeout <= 1 or not 0 < write_timeout <= 30:
            raise ValueError("Invalid serial timeout")
        self.read_timeout, self.write_timeout = read_timeout, write_timeout
        self._serial = None

    async def open(self):
        if self._serial is not None:
            return
        try:
            import serial
        except ImportError as error:
            raise TransportError("Install zk-rfid-sdk[serial] on CPython") from error

        def create():
            return serial.Serial(
                self.port,
                self.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=self.read_timeout,
                write_timeout=self.write_timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )

        task = asyncio.create_task(asyncio.to_thread(create))
        try:
            self._serial = await asyncio.shield(task)
        except asyncio.CancelledError:
            # Do not leak a serial handle opened by a still-running worker.
            opened = await task
            await asyncio.to_thread(opened.close)
            raise
        except Exception as error:
            raise TransportError(f"Cannot open {self.port}: {error}") from error

    async def read(self, size=4096) -> bytes:
        while self._serial is not None:
            port = self._serial
            try:
                data = await asyncio.to_thread(port.read, min(size, max(1, port.in_waiting)))
            except Exception as error:
                if self._serial is None:
                    return b""
                raise TransportError(f"Serial read failed: {error}") from error
            if data:
                return data
            # A serial timeout is not EOF; loop has awaited the worker.
        return b""

    async def write(self, data: bytes) -> int:
        if self._serial is None:
            raise TransportError("Serial port is closed")
        try:
            return await asyncio.to_thread(self._serial.write, data)
        except Exception as error:
            raise TransportError(f"Serial write failed: {error}") from error

    async def set_baudrate(self, baudrate: int):
        if self._serial is None:
            raise TransportError("Serial port is closed")
        await asyncio.to_thread(setattr, self._serial, "baudrate", baudrate)
        self.baudrate = baudrate

    async def close(self):
        port, self._serial = self._serial, None
        if port is not None:

            def close_port():
                if hasattr(port, "cancel_read"):
                    port.cancel_read()
                if hasattr(port, "cancel_write"):
                    port.cancel_write()
                port.close()

            await asyncio.to_thread(close_port)
