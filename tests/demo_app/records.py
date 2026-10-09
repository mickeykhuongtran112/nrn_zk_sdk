"""Bounded event history + queue-backed rotating JSONL audit outside the RX task."""

import csv
import io
import json
import logging
import logging.handlers
import queue
import threading
import time
from collections import deque
from pathlib import Path
from .catalog import plain


class AuditHandler(logging.handlers.RotatingFileHandler):
    def handleError(self, record):
        # logging normally suppresses disk errors; surface them in the console.
        import sys

        self.owner.disk_error = str(sys.exception())


class EventLog:
    def __init__(self, path: Path | None = None, capacity=5000):
        self.events = deque(maxlen=capacity)
        self.sequence = 0
        self.lock = threading.Lock()
        self.path = path
        self.write_queue = queue.Queue(maxsize=20000)
        self.disk_dropped = 0
        self.disk_error = None
        self.writer = None
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.handler = AuditHandler(path, maxBytes=10_000_000, backupCount=3, encoding="utf-8")
            self.handler.owner = self
            self.handler.setFormatter(logging.Formatter("%(message)s"))
            self.writer = threading.Thread(target=self._write, name="zk-demo-log", daemon=True)
            self.writer.start()

    def append(self, kind, **payload):
        data = plain(payload)
        with self.lock:
            self.sequence += 1
            event = {"id": self.sequence, "wall_time": time.time(), "kind": kind, **data}
            self.events.append(event)
        if self.writer:
            try:
                self.write_queue.put_nowait(event)
            except queue.Full:
                self.disk_dropped += 1
        return event

    def _write(self):
        while True:
            item = self.write_queue.get()
            try:
                if item is None:
                    return
                self.handler.emit(
                    logging.makeLogRecord(
                        {"msg": json.dumps(item, ensure_ascii=False, allow_nan=False)}
                    )
                )
            except Exception as e:
                self.disk_error = str(e)
            finally:
                self.write_queue.task_done()

    def since(self, cursor, limit=500):
        with self.lock:
            first = self.events[0]["id"] if self.events else self.sequence + 1
            result = [e for e in self.events if e["id"] > cursor][:limit]
            missed = max(0, first - cursor - 1) if cursor else 0
            return {
                "events": result,
                "next": result[-1]["id"] if result else max(cursor, self.sequence),
                "missed": missed,
                "latest": self.sequence,
                "disk_dropped": self.disk_dropped,
                "disk_error": self.disk_error,
            }

    def export(self):
        with self.lock:
            events = list(self.events)
        metadata = {
            "kind": "export_metadata",
            "retained_events": len(events),
            "bounded_history": True,
            "disk_log": str(self.path) if self.path else None,
            "disk_dropped": self.disk_dropped,
            "disk_error": self.disk_error,
        }
        return (
            "\n".join(
                json.dumps(e, ensure_ascii=False, allow_nan=False) for e in [metadata, *events]
            )
            + "\n"
        )

    def close(self):
        if self.writer:
            self.write_queue.put(None, timeout=5)
            self.writer.join(timeout=5)
            if self.writer.is_alive():
                self.disk_error = "Writer did not finish within 5 seconds"
            else:
                self.handler.close()


def tags_csv(rows):
    out = io.StringIO(newline="")
    names = [
        "epc",
        "tid",
        "antenna",
        "count",
        "rssi_raw",
        "rssi_dbm",
        "rssi_source",
        "rssi_in_calibration_range",
        "phase_raw",
        "phase_begin_raw",
        "phase_end_raw",
        "phase_begin_degrees",
        "phase_end_degrees",
        "phase_begin_radians",
        "phase_end_radians",
        "phase_conversion",
        "frequency_khz",
        "memory_data",
        "first_seen",
        "last_seen",
    ]
    writer = csv.DictWriter(out, fieldnames=names, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return out.getvalue()
