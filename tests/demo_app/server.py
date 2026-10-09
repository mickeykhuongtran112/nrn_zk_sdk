"""Loopback-only stdlib HTTP host; transport remains owned by one asyncio loop."""

import asyncio
import concurrent.futures
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from zk_rfid import PROFILES, SDK_VERSION, StateError, ValidationError

from .catalog import LIMITATIONS, catalogue, plain
from .controller import Controller
from .records import tags_csv

STATIC = Path(__file__).parent / "static"
STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
API_REVISION = 2


class Runtime:
    def __init__(self, log, defaults=None, transport_factory=None):
        self.loop = asyncio.new_event_loop()
        self.controller = Controller(log, defaults, transport_factory)
        self.thread = threading.Thread(target=self._run, name="zk-demo-async", daemon=True)
        self.thread.start()
        self.watchdog = asyncio.run_coroutine_threadsafe(self.controller.watchdog(), self.loop)

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        self.loop.run_until_complete(self.loop.shutdown_default_executor())
        self.loop.close()

    async def _snapshot(self, include_tags=True, result_after=None):
        self.controller.browser_seen = time.monotonic()
        return self.controller.snapshot(include_tags=include_tags, result_after=result_after)

    def snapshot(self, include_tags=True, result_after=None):
        return self.call(self._snapshot(include_tags, result_after))

    async def _tags(self):
        return list(self.controller.tags.values())

    def call(self, coroutine, timeout=10):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(timeout)

    def close(self):
        try:
            self.call(self.controller.shutdown(), timeout=130)
        finally:
            self.watchdog.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=10)
            self.controller.log.close()


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, runtime, port=8765):
        self.runtime = runtime
        self.token = secrets.token_urlsafe(32)
        # Keep the UI paired with the loaded Python handlers until restart.
        # Reading assets on every request mixes new JS with an old API process.
        self.assets = {
            route: ((STATIC / filename).read_bytes(), content)
            for route, (filename, content) in STATIC_ROUTES.items()
        }
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "ZKSDKDemo/1"

    def log_message(self, *args):
        pass

    def trusted_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def authorized(self):
        origin = self.headers.get("Origin")
        port = self.server.server_port
        return (
            self.trusted_host()
            and self.headers.get("X-Demo-Token") == self.server.token
            and (
                origin is None or origin in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")
            )
        )

    def send_bytes(
        self, data, content_type="application/json; charset=utf-8", code=200, filename=None
    ):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
        )
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json(self, obj, code=200):
        self.send_bytes(
            json.dumps(plain(obj), ensure_ascii=False, allow_nan=False).encode("utf-8"), code=code
        )

    def live_stream(self):
        # Dedicated HTTP writer: a slow socket never blocks serial RX or the
        # asyncio loop. No raw event backlog: updates contain cumulative rows.
        self.connection.settimeout(5)
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        cursor = None
        try:
            while True:
                packet = self.server.runtime.call(
                    self.server.runtime.controller.live_update(cursor)
                )
                self.wfile.write((json.dumps(packet, allow_nan=False) + "\n").encode("utf-8"))
                self.wfile.flush()
                cursor = packet["cursor"]
                if packet["closed"]:
                    break
        except (OSError, TimeoutError, concurrent.futures.CancelledError):
            pass

    def do_GET(self):
        if not self.trusted_host():
            return self.json({"error": "Invalid host"}, 403)
        url = urlsplit(self.path)
        if url.path in self.server.assets:
            data, content = self.server.assets[url.path]
            return self.send_bytes(data, content)
        if url.path == "/api/bootstrap":
            return self.json(
                {
                    "token": self.server.token,
                    "version": SDK_VERSION,
                    "api_revision": API_REVISION,
                    "features": {"live_tags": True},
                    "catalogue": catalogue(),
                    "limitations": LIMITATIONS,
                    "profiles": plain(list(PROFILES.values())),
                    "defaults": self.server.runtime.controller.defaults,
                }
            )
        if not self.authorized():
            return self.json({"error": "Local session token required"}, 403)
        try:
            runtime = self.server.runtime
            if url.path == "/api/live":
                return self.live_stream()
            if url.path == "/api/snapshot":
                query = parse_qs(url.query)
                return self.json(
                    runtime.snapshot(
                        query.get("tags") != ["0"], query.get("result_after", [None])[0]
                    )
                )
            if url.path == "/api/events":
                cursor = int(parse_qs(url.query).get("after", ["0"])[0])
                if cursor < 0:
                    raise ValueError("Invalid event cursor")
                return self.json(runtime.controller.log.since(cursor))
            if url.path == "/api/ports":
                from serial.tools import list_ports

                return self.json(
                    [
                        {"port": p.device, "description": p.description}
                        for p in list_ports.comports()
                    ]
                )
            if url.path == "/api/logs":
                return self.send_bytes(
                    runtime.controller.log.export().encode("utf-8"),
                    "application/x-ndjson",
                    filename="zk-events.jsonl",
                )
            if url.path == "/api/tags.csv":
                return self.send_bytes(
                    ("\ufeff" + tags_csv(runtime.call(runtime._tags()))).encode("utf-8"),
                    "text/csv; charset=utf-8",
                    filename="zk-tags.csv",
                )
            return self.json({"error": "Not found"}, 404)
        except Exception as error:
            return self.json({"error": type(error).__name__, "message": str(error)}, 400)

    def do_POST(self):
        if not self.authorized():
            return self.json({"error": "Invalid local session or origin"}, 403)
        if urlsplit(self.path).path != "/api/operation":
            return self.json({"error": "Not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                return self.json({"error": "Request body must be 1..65536 bytes"}, 413)
            if self.headers.get_content_type() != "application/json":
                return self.json({"error": "JSON content type required"}, 415)
            request = json.loads(
                self.rfile.read(length),
                parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON")),
            )
            if not isinstance(request, dict):
                raise ValidationError("Request must be an object")
            result = self.server.runtime.call(
                self.server.runtime.controller.submit(
                    request.get("operation"), request.get("arguments", {}), request.get("intent")
                )
            )
            return self.json(result, 202)
        except (ValidationError, ValueError, TypeError) as error:
            return self.json({"error": type(error).__name__, "message": str(error)}, 400)
        except StateError as error:
            return self.json({"error": type(error).__name__, "message": str(error)}, 409)
        except concurrent.futures.TimeoutError:
            return self.json(
                {"error": "Service busy; inspect state before retrying a mutation"}, 503
            )
        except Exception as error:
            return self.json({"error": type(error).__name__, "message": str(error)}, 500)
