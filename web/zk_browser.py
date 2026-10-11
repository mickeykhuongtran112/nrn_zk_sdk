"""Pyodide boundary for zk_rfid.py. No reader protocol is implemented here."""

import asyncio
import inspect
import json
from dataclasses import fields, is_dataclass
from enum import Enum

from zk_rfid import (
    InventoryConfig,
    InventoryData,
    InventoryMode,
    MemoryBank,
    QueryParameters,
    ReaderCapabilities,
    RealTimeConfig,
    Region,
    ScanParameters,
    StateError,
    TagMask,
    TagReport,
    TagTarget,
    TIDParameters,
    ValidationError,
    WorkingMode,
    ZKReader,
)


def plain(value):
    if isinstance(value, bytes):
        return value.hex().upper()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def hex_bytes(value):
    if not isinstance(value, str):
        raise ValidationError("Byte parameters must be hexadecimal strings")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValidationError("Invalid hexadecimal bytes") from error


def model(cls, value):
    if not isinstance(value, dict):
        raise ValidationError(f"{cls.__name__} requires an object")
    args = dict(value)
    if args.get("mask") is not None:
        args["mask"] = model(TagMask, args["mask"])
    if cls is TagTarget and args.get("epc") is not None:
        args["epc"] = hex_bytes(args["epc"])
    if cls is TagMask:
        args["data"] = hex_bytes(args["data"])
    if cls is InventoryConfig:
        if "data" in args:
            args["data"] = InventoryData(args["data"])
        if "access_password" in args:
            args["access_password"] = hex_bytes(args["access_password"])
        if "memory_bank" in args:
            args["memory_bank"] = MemoryBank(args["memory_bank"])
    return cls(**args)


METHODS = frozenset(
    name
    for name, value in inspect.getmembers(ZKReader, inspect.isfunction)
    if not name.startswith("_") and name not in ("open", "close")
)


def arguments(operation, values):
    if operation not in METHODS:
        raise ValidationError("Unknown SDK operation; use connect/disconnect for lifecycle")
    if not isinstance(values, dict):
        raise ValidationError("Arguments must be an object")
    inspect.signature(getattr(ZKReader, operation)).bind(None, **values)
    result = dict(values)
    for key, value in values.items():
        if value is None:
            continue
        if key in {
            "epc",
            "data",
            "access_password",
            "verification_password",
            "new_password",
            "kill_password",
        }:
            result[key] = hex_bytes(value)
        elif key in ("target", "verification_target"):
            result[key] = model(TagTarget, value)
        elif key == "mask" and operation != "set_antennas":
            result[key] = model(TagMask, value)
        elif key == "config":
            result[key] = model(
                RealTimeConfig if operation == "set_real_time_config" else InventoryConfig, value
            )
        elif key == "parameters":
            result[key] = model(
                {
                    "set_scan_parameters": ScanParameters,
                    "set_query_parameters": QueryParameters,
                    "set_tid_parameters": TIDParameters,
                }[operation],
                value,
            )
        elif key == "region":
            result[key] = model(Region, value)
        elif key == "mode":
            result[key] = (
                InventoryMode(value) if operation == "start_inventory" else WorkingMode(value)
            )
        elif key == "data_kind":
            result[key] = InventoryData(value)
        elif key == "bank":
            result[key] = MemoryBank(value)
        elif key == "profile_ids" or key == "power_dbm" and isinstance(value, list):
            result[key] = tuple(value)
    return result


class WebSerialTransport:
    def __init__(self, io):
        self.io = io

    async def open(self):
        await self.io.open()

    async def close(self):
        await self.io.close()

    async def read(self, size=4096):
        value = await self.io.read(size)
        return bytes(value.to_py())

    async def write(self, data):
        from pyodide.ffi import to_js

        return await self.io.write(to_js(data))

    # No set_baudrate: SDK rejects a baud change BEFORE transmitting 0x28.
    # Web Serial cannot update baud on an open SerialPort.


class BrowserReader:
    def __init__(self, io, options_json, notify):
        options = json.loads(options_json)
        self.notify = notify
        self.consumer = None
        self.session = None
        self.reader = ZKReader(
            WebSerialTransport(io),
            address=options.get("address", 0),
            timeout=options.get("timeout", 3),
            capabilities=ReaderCapabilities(**options.get("capabilities", {})),
            on_event=lambda event: self.emit("trace", event),
        )

    def emit(self, kind, data):
        self.notify(kind, json.dumps(plain(data)))

    def envelope(self, *, data=None, error=None):
        return json.dumps(
            {
                "ok": error is None,
                "data": plain(data),
                "error": error,
                "state": self.reader.state.value,
            }
        )

    def failure(self, error):
        return self.envelope(
            error={
                "type": type(error).__name__,
                "message": str(error),
                "result": plain(getattr(error, "result", None)),
                "transmitted": getattr(error, "transmitted", None),
            }
        )

    async def open(self, recover=False):
        try:
            await self.reader.open(recover=recover)
            return self.envelope(data=self.reader.get_capabilities())
        except Exception as error:
            return self.failure(error)

    async def consume(self, session):
        try:
            async for report in session:
                self.emit("tag" if isinstance(report, TagReport) else "heartbeat", report)
        except Exception as error:
            # A dead consumer must not leave a healthy reader inventorying indefinitely.
            outcome = None
            try:
                outcome = await session.stop()
                for report in session.drain():
                    self.emit("tag" if isinstance(report, TagReport) else "heartbeat", report)
            finally:
                self.emit("state", {"state": self.reader.state.value})
                self.emit(
                    "error",
                    {
                        "type": type(error).__name__,
                        "message": str(error),
                        "inventory_outcome": outcome,
                    },
                )

    async def call(self, operation, args_json):
        try:
            args = arguments(operation, json.loads(args_json))
            if operation == "start_inventory":
                if self.consumer and not self.consumer.done():
                    raise StateError("Inventory is already running")
                self.session = await self.reader.start_inventory(**args)
                self.consumer = asyncio.create_task(self.consume(self.session))
                return self.envelope(data={"started": True, "mode": self.session.mode.value})
            value = getattr(self.reader, operation)(**args)
            if inspect.isawaitable(value):
                value = await value
            if operation == "stop_inventory" and self.consumer:
                await self.consumer
                self.consumer = None
            if operation == "stop_inventory" and value.termination_reason == "already_idle":
                if self.session is not None and self.session.outcome is not None:
                    value = self.session.outcome
            return self.envelope(data=value)
        except Exception as error:
            return self.failure(error)

    async def close(self):
        try:
            await self.reader.close()
            return self.envelope(
                data={
                    "inventory_outcome": self.session.outcome
                    if self.session is not None
                    else getattr(self.reader, "last_inventory_outcome", None),
                    "fault": str(self.reader.dispatcher.fault)
                    if self.reader.dispatcher.fault
                    else None,
                }
            )
        except Exception as error:
            return self.failure(error)
        finally:
            if self.consumer:
                if not self.consumer.done():
                    self.consumer.cancel()
                await asyncio.gather(self.consumer, return_exceptions=True)
                self.consumer = None
