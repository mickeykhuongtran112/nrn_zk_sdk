"""Live view isolation, exact counters, reset/reconnect and real HTTP streaming."""

import asyncio
import json
import threading
import urllib.request
import urllib.error
import pytest
from zk_rfid import TagReport
from tests.demo_app.controller import Controller
from tests.demo_app.live import LiveView
from tests.demo_app.records import EventLog
from tests.demo_app.server import Runtime, DemoServer


@pytest.mark.asyncio
async def test_slow_view_is_bounded_and_resync_keeps_exact_counts():
    c = Controller(EventLog(capacity=3))
    c.live.interval = 0
    initial = await c.live_update()
    report = TagReport(epc=b"\xab\xcd", antenna_mask=1, rssi_raw=110)
    # A slow browser and an overflowing log ring must not block or lose reads.
    for _ in range(20000):
        c.add_tag(report)
    update = await c.live_update(tuple(initial["cursor"]))
    assert not update["reset"] and len(update["rows"]) == 1
    assert update["received_count"] == update["rows"][0]["count"] == 20000
    assert len(c.live.rows) == len(c.tags) == 1
    assert c.log.since(1)["missed"] > 0
    # Two reconnecting browsers independently obtain current authoritative data.
    a, b = await asyncio.gather(c.live_update(), c.live_update())
    assert a == b and a["reset"] and a["rows"][0]["count"] == 20000
    assert "tags" not in c.snapshot(include_tags=False)
    await c._execute("clear_tags", {})
    cleared = await c.live_update(tuple(a["cursor"]))
    assert cleared["reset"] and cleared["received_count"] == 0 and not cleared["rows"]
    assert c.snapshot()["tag_generation"] == cleared["cursor"][0] != a["cursor"][0]
    c.add_tag(report)
    after_clear = await c.live_update(tuple(cleared["cursor"]))
    assert after_clear["rows"][0]["count"] == after_clear["received_count"] == 1


@pytest.mark.asyncio
async def test_multiple_waiters_and_reset_during_coalescing():
    view = LiveView(capacity=2, interval=0.01)
    initial = await view.next()
    first = asyncio.create_task(view.next(initial["cursor"]))
    second = asyncio.create_task(view.next(initial["cursor"]))
    await asyncio.sleep(0)
    view.update("a", {"count": 1})
    view.update("b", {"count": 2})
    view.update("c", {"count": 3})
    a, b = await asyncio.wait_for(asyncio.gather(first, second), 0.5)
    assert a == b and len(a["rows"]) == 2 and len(view.rows) == 2
    view.update("a", {"count": 4})
    pending = asyncio.create_task(view.next(a["cursor"]))
    await asyncio.sleep(0)
    view.reset()
    result = await pending
    assert result["reset"] and result["rows"] == []


def test_live_http_auth_first_packet_and_independent_log_route():
    runtime = Runtime(EventLog())
    server = DemoServer(runtime, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    async def add_reports():
        for _ in range(100):
            runtime.controller.add_tag(TagReport(epc=b"\xab\xcd", antenna_mask=1))

    try:
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(base + "/api/live", timeout=2)
        assert error.value.code == 403
        headers = {"X-Demo-Token": server.token}
        request = urllib.request.Request(base + "/api/live", headers=headers)
        with urllib.request.urlopen(request, timeout=2) as stream:
            assert stream.headers.get_content_type() == "application/x-ndjson"
            first = json.loads(stream.readline())
            assert first["reset"] and first["received_count"] == 0
            runtime.call(add_reports())
            update = json.loads(stream.readline())
            assert update["rows"][0]["count"] == update["received_count"] == 100
            log_request = urllib.request.Request(base + "/api/events", headers=headers)
            with urllib.request.urlopen(log_request, timeout=2) as log:
                assert len(json.load(log)["events"]) == 100
        with urllib.request.urlopen(request, timeout=2) as stream:
            synced = json.loads(stream.readline())
            assert synced["reset"] and synced["received_count"] == 100
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        runtime.close()


def test_http_assets_stay_paired_with_loaded_server_until_restart(tmp_path, monkeypatch):
    from tests.demo_app import server as module

    monkeypatch.setattr(module, "STATIC", tmp_path)
    for filename, _ in module.STATIC_ROUTES.values():
        (tmp_path / filename).write_bytes(b"original UI")
    runtime = Runtime(EventLog())
    first = DemoServer(runtime, 0)
    for filename, _ in module.STATIC_ROUTES.values():
        (tmp_path / filename).write_bytes(b"updated UI")
    second = DemoServer(runtime, 0)
    threads = []
    try:
        for server, expected in ((first, b"original UI"), (second, b"updated UI")):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            threads.append(thread)
            for route in module.STATIC_ROUTES:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{server.server_port}{route}", timeout=2
                ) as response:
                    assert response.read() == expected
    finally:
        for server, thread in zip((first, second), threads):
            server.shutdown()
            thread.join(timeout=3)
        first.server_close()
        second.server_close()
        runtime.close()
