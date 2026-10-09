"""One asyncio-owned reader; HTTP/UI can never read serial bytes independently."""

import asyncio
import inspect
import math
import time
from collections import OrderedDict
from zk_rfid import ZKReader, ReaderCapabilities, InventoryOutcome, TagReport, WorkingMode
from zk_rfid.errors import StateError, ValidationError, OperationError, ExchangeError
from zk_rfid.protocol.status import interpret_status
from zk_rfid.transports.serial import SerialTransport
from .catalog import convert, plain, OP_GROUP, TAG_WRITES, DESTRUCTIVE
from .simulator import DemoTransport
from .live import LiveView


class Controller:
    def __init__(self, log, defaults=None, transport_factory=None):
        self.log, self.defaults = (
            log,
            defaults or {"port": "COM13", "baud": 115200, "ports": 1, "address": 0, "timeout": 5},
        )
        self.transport_factory = transport_factory
        self.reader = None
        self.transport = None
        self.session = None
        self.consumer = None
        self.last_stream_health = {"received": 0, "dropped": 0, "queued": 0, "error": None}
        self.connection = None
        self.recovery_required = False
        self.uncertain_ports = set()
        self.tasks, self.jobs = {}, OrderedDict()
        self.job_sequence = 0
        self.busy = None
        self.control_busy = None
        self.tags = OrderedDict()
        self.live = LiveView()
        self.received_count, self.tag_overflow = 0, 0
        self.last_result = None
        self.browser_seen = time.monotonic()
        self.shutting_down = False

    def trace(self, event):
        data = plain(event)
        kind = data.pop("kind")
        if event.status is not None and event.command is not None:
            data["status_name"] = interpret_status(event.command, event.status).name
        self.log.append(kind, trace=data)

    def snapshot(self, *, include_tags=True, result_after=None):
        r = self.reader
        return {
            "connection": self.connection,
            "connected": bool(r and r.dispatcher.opened),
            "state": r.state.value if r else "disconnected",
            "state_basis": "SDK host lifecycle; saved reader mode shown separately",
            "working_mode": plain(r._working_mode) if r else None,
            "address": r.address if r else None,
            "baud": getattr(self.transport, "baudrate", None),
            "fault": str(r.dispatcher.fault) if r and r.dispatcher.fault else None,
            "recovery_required": self.recovery_required or bool(r and r.dispatcher.fault),
            "pending_command": r.dispatcher.pending_command if r else None,
            "diagnostics": plain(r.dispatcher.parser.diagnostics) if r else {},
            "observer_errors": r.dispatcher.trace.observer_errors if r else 0,
            "busy": self.control_busy or self.busy,
            "control_busy": self.control_busy,
            "uncertain_ports": sorted(self.uncertain_ports),
            "session": self.session.mode.value if self.session else None,
            "stream_health": {
                "received": self.session._received,
                "dropped": self.session._dropped,
                "queued": self.session.queue.qsize(),
                "error": str(self.session._error) if self.session._error else None,
            }
            if self.session
            else self.last_stream_health,
            "received_count": self.received_count,
            "unique_ids": len(self.tags),
            "tag_generation": self.live.generation,
            "tag_overflow": self.tag_overflow,
            **({"tags": list(self.tags.values())[:1000]} if include_tags else {}),
            "jobs": [
                {k: v for k, v in job.items() if k in {"id", "operation", "state", "finished"}}
                for job in list(self.jobs.values())[-30:]
            ],
            **(
                {"last_result": self.last_result}
                if not self.last_result or self.last_result.get("job_id") != result_after
                else {}
            ),
            "log_path": str(self.log.path) if self.log.path else None,
        }

    async def live_update(self, cursor=None):
        packet = await self.live.next(cursor)
        self.browser_seen = time.monotonic()
        return {
            **packet,
            "received_count": self.received_count,
            "unique_ids": len(self.tags),
            "tag_overflow": self.tag_overflow,
            "closed": self.shutting_down,
        }

    async def submit(self, operation, arguments=None, intent=None):
        if self.shutting_down:
            raise StateError("Demo server is shutting down")
        if (
            not isinstance(operation, str)
            or operation not in OP_GROUP
            and operation
            not in {
                "connect",
                "disconnect",
                "clear_tags",
                "inject",
            }
        ):
            raise ValidationError("Unknown operation")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ValidationError("Arguments must be an object")
        if self.control_busy and operation != "clear_tags":
            raise StateError("Stop/disconnect is still completing")
        if (
            self.busy
            and self.jobs[self.busy]["operation"] == "connect"
            and operation != "clear_tags"
        ):
            raise StateError("Connection is still opening")
        if self.busy and operation not in {"stop_inventory", "disconnect", "clear_tags"}:
            raise StateError("Another operation is active; wait or use Stop")
        if operation == "connect" and self.reader and self.reader.dispatcher.opened:
            raise StateError("Disconnect before connecting another transport")
        if operation in TAG_WRITES:
            if not isinstance(intent, dict) or intent.get("allow_tag_write") is not True:
                raise ValidationError("Enable tag writes in this request before transmitting")
            if operation in DESTRUCTIVE and intent.get("confirmation") != DESTRUCTIVE[operation]:
                raise ValidationError(
                    "Type " + DESTRUCTIVE[operation] + " to confirm this tag operation"
                )
            if operation == "write_epc_single":
                if intent.get("single_tag") is not True:
                    raise ValidationError(
                        "Native WriteEPC requires exactly one physical tag in the field"
                    )
            elif not (arguments or {}).get("target"):
                raise ValidationError("Demo tag writes require an explicit EPC/TID/mask target")
        # Validate object topology before assigning a job; SDK validates wire bounds before TX.
        converted = (
            convert(operation, arguments or {}) if operation in OP_GROUP else arguments or {}
        )
        self.job_sequence += 1
        job_id = str(self.job_sequence)
        job = {"id": job_id, "operation": operation, "state": "running", "started": time.time()}
        self.jobs[job_id] = job
        while len(self.jobs) > 256:
            self.jobs.popitem(last=False)
        if operation not in {"stop_inventory", "clear_tags", "disconnect"}:
            self.busy = job_id
        if operation in {"stop_inventory", "disconnect"}:
            self.control_busy = job_id
        self.log.append(
            "operation",
            job_id=job_id,
            operation=operation,
            arguments=arguments or {},
            source="simulator" if self.connection and self.connection["simulate"] else "serial",
        )
        task = asyncio.create_task(self._job(job, converted), name="zk-demo-job-" + job_id)
        self.tasks[job_id] = task
        task.add_done_callback(lambda _: self.tasks.pop(job_id, None))
        return {"job_id": job_id, "accepted": True}

    async def _job(self, job, arguments):
        prior_fault = self.reader.dispatcher.fault if self.reader else None
        try:
            result = await self._execute(job["operation"], arguments)
            value = plain(result)
            if isinstance(result, InventoryOutcome):
                for report in result.reports:
                    self.add_tag(report)
            if hasattr(result, "outcome"):
                job["state"] = result.outcome.value
            else:
                job["state"] = "success"
            job["result"] = value
            self.last_result = {"job_id": job["id"], "operation": job["operation"], "result": value}
            self.log.append(
                "operation_result",
                job_id=job["id"],
                operation=job["operation"],
                outcome=job["state"],
                result=value,
            )
        except asyncio.CancelledError:
            job["state"] = "cancelled"
            value = plain(self.reader.last_result) if self.reader else None
            job["result"] = value
            self.log.append("operation_cancelled", job_id=job["id"], result=value)
            raise
        except Exception as error:
            job["state"] = "failure"
            job["error"] = {"type": type(error).__name__, "message": str(error)}
            if isinstance(error, OperationError):
                job["error"]["result"] = plain(error.result)
                job["state"] = error.result.outcome.value
            elif isinstance(error, ExchangeError) and error.transmitted:
                job["state"] = "unknown"
            elif (
                not isinstance(error, (ValidationError, StateError))
                and self.reader
                and self.reader.dispatcher.fault
                and self.reader.dispatcher.fault is not prior_fault
            ):
                job["state"] = "unknown"
            self.last_result = {
                "job_id": job["id"],
                "operation": job["operation"],
                "error": job["error"],
                "outcome": job["state"],
            }
            self.log.append(
                "operation_error",
                job_id=job["id"],
                operation=job["operation"],
                outcome=job["state"],
                error=job["error"],
            )
        finally:
            job["finished"] = time.time()
            if self.busy == job["id"]:
                self.busy = None
            if self.control_busy == job["id"]:
                self.control_busy = None
            self._remember_fault()

    def _remember_fault(self):
        if self.reader and self.reader.dispatcher.fault:
            self.recovery_required = True
            if self.connection and not self.connection["simulate"]:
                self.uncertain_ports.add(self.connection["port"].upper())

    async def _execute(self, operation, arguments):
        if operation == "connect":
            return await self.connect(arguments)
        if operation == "disconnect":
            return await self.disconnect()
        if operation == "clear_tags":
            self.tags.clear()
            self.received_count, self.tag_overflow = 0, 0
            self.live.reset()
            return {"cleared": "host tag table only"}
        if operation == "inject":
            if not isinstance(self.transport, DemoTransport):
                raise ValidationError("Fault injection is only available in the simulator")
            if arguments.get("error") not in ("failure", "tag_error", "partial", "timeout"):
                raise ValidationError("Unknown simulation fault")
            self.transport.inject = arguments["error"]
            return {"next_simulated_response": arguments["error"]}
        if not self.reader or not self.reader.dispatcher.opened:
            raise StateError("Connect first")
        if self.recovery_required:
            raise StateError("Unknown reader state; establish a clean boundary, then reconnect")
        if isinstance(self.transport, DemoTransport) and "config" in arguments:
            if operation in ("start_inventory", "inventory_once", "inventory_to_buffer"):
                self.transport.inventory_config = arguments["config"]
        if operation == "start_inventory":
            self.session = await self.reader.start_inventory(**arguments)
            self.consumer = asyncio.create_task(self._consume(self.session), name="zk-demo-tags")
            return {"started": self.session.mode.value, "confirmation": "SDK session started"}
        if operation == "stop_inventory":
            if not self.session and self.reader._working_mode in (
                WorkingMode.REAL_TIME,
                WorkingMode.TRIGGER,
            ):
                # Direct mode API has no session owner; 0x76 Answer is the native stop.
                result = await self.reader.set_working_mode(WorkingMode.ANSWER)
            else:
                result = await self.reader.stop_inventory()
            if self.consumer:
                await asyncio.gather(self.consumer, return_exceptions=True)
                self.consumer = None
            self.session = None
            return result
        method = getattr(self.reader, operation)
        result = method(**arguments)
        return await result if inspect.isawaitable(result) else result

    async def connect(self, values):
        allowed = {
            "port",
            "baud",
            "ports",
            "address",
            "timeout",
            "simulate",
            "clean_boundary",
            "cfg25_length",
            "cfg29_length",
            "buffer_antenna_bytes",
            "model",
            "firmware",
        }
        if set(values) - allowed:
            raise ValidationError("Unknown connection option")
        args = {**self.defaults, **values}
        simulate = args.get("simulate", False)
        if not isinstance(simulate, bool):
            raise ValidationError("simulate must be boolean")
        if not isinstance(args["port"], str) or not args["port"].strip():
            raise ValidationError("Serial port must be nonempty text")
        port_key = args["port"].strip().upper()
        if (
            port_key in self.uncertain_ports
            and not simulate
            and args.get("clean_boundary") is not True
        ):
            raise StateError(
                "Confirm a reset/clean device boundary before reconnecting after an uncertain exchange"
            )
        timeout = args["timeout"]
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or not 0 < timeout <= 120
        ):
            raise ValidationError("Timeout must be finite, 0 < seconds <= 120")
        caps = ReaderCapabilities(
            antenna_ports=args["ports"],
            model=args.get("model"),
            firmware=args.get("firmware"),
            cfg25_length=args.get("cfg25_length"),
            cfg29_length=args.get("cfg29_length"),
            buffer_antenna_bytes=args.get("buffer_antenna_bytes"),
        )
        self.transport = (
            self.transport_factory(args)
            if self.transport_factory
            else DemoTransport(args["ports"])
            if simulate
            else SerialTransport(args["port"], args["baud"])
        )
        if simulate and isinstance(self.transport, DemoTransport):
            self.transport.address = args["address"]
        self.reader = ZKReader(
            self.transport,
            address=args["address"],
            capabilities=caps,
            timeout=timeout,
            on_event=self.trace,
        )
        try:
            await self.reader.open()
        except BaseException:
            self.reader = None
            raise
        self.recovery_required = False
        if not simulate:
            self.uncertain_ports.discard(port_key)
        self.connection = {
            "port": args["port"].strip(),
            "baud": args["baud"],
            "ports": args["ports"],
            "simulate": simulate,
            "source": "synthetic" if simulate else "hardware",
        }
        self.tags.clear()
        self.received_count, self.tag_overflow = 0, 0
        self.live.reset()
        self.last_stream_health = {"received": 0, "dropped": 0, "queued": 0, "error": None}
        self.log.append("connection", **self.connection)
        return {
            "connected": True,
            **self.connection,
            "note": "No configuration command sent automatically",
        }

    async def disconnect(self):
        if self.reader:
            reader = self.reader
            self._remember_fault()
            try:
                if (
                    reader.dispatcher.opened
                    and not reader.dispatcher.fault
                    and not self.session
                    and reader._working_mode in (WorkingMode.REAL_TIME, WorkingMode.TRIGGER)
                ):
                    result = await reader.set_working_mode(WorkingMode.ANSWER)
                    self.log.append("disconnect_mode_stop", result=plain(result))
                await reader.close()
            finally:
                if reader.dispatcher.opened:
                    await reader.close()
                self._remember_fault()
                if self.consumer:
                    self.consumer.cancel()
                    await asyncio.gather(self.consumer, return_exceptions=True)
                self.consumer, self.session = None, None
        return {"connected": False, "recovery_required": self.recovery_required}

    def add_tag(self, report):
        self.received_count += 1
        row = plain(report)
        self.log.append("tag", report=row)
        key = (row["epc"], row["tid"], row["antenna_mask"])
        now = time.time()
        if key not in self.tags:
            if len(self.tags) >= 5000:
                self.tag_overflow += 1
                self.live.update(key, row)
                return
            self.tags[key] = {**row, "count": 0, "first_seen": now}
        old = self.tags[key]
        self.tags[key] = {**old, **row, "count": old["count"] + 1, "last_seen": now}
        self.live.update(key, self.tags[key])

    async def _consume(self, session):
        try:
            async for report in session:
                if isinstance(report, TagReport):
                    self.add_tag(report)
                else:
                    self.log.append("heartbeat", report=plain(report))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.log.append(
                "inventory_error", error={"type": type(error).__name__, "message": str(error)}
            )
            # Queue overflow must still stop RF; never leave a broken consumer running.
            try:
                result = await session.stop()
                self.log.append("inventory_auto_stop", result=plain(result))
            except Exception as stop_error:
                self.log.append("inventory_stop_error", error=str(stop_error))
            self._remember_fault()
        finally:
            self.last_stream_health = {
                "received": session._received,
                "dropped": session._dropped,
                "queued": session.queue.qsize(),
                "error": str(session._error) if session._error else None,
            }
            if self.session is session:
                self.session = None

    async def watchdog(self):
        while not self.shutting_down:
            await asyncio.sleep(2)
            active = self.session or (
                self.reader
                and self.reader.dispatcher.opened
                and self.reader._working_mode in (WorkingMode.REAL_TIME, WorkingMode.TRIGGER)
            )
            if (
                active
                and not self.control_busy
                and not self.recovery_required
                and time.monotonic() - self.browser_seen > 30
            ):
                self.log.append(
                    "browser_lost", detail="No browser heartbeat for 30 seconds; stopping inventory"
                )
                try:
                    accepted = await self.submit("stop_inventory")
                    task = self.tasks.get(accepted["job_id"])
                    if task:
                        await task
                except Exception as error:
                    self.log.append("watchdog_error", error=str(error))

    async def shutdown(self):
        self.shutting_down = True
        self.live.notify()
        try:
            await self.disconnect()
        finally:
            tasks = list(self.tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
