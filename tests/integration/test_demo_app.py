import asyncio
import csv
import inspect
import io
import json
import threading
import urllib.error
import urllib.request

import pytest

from tests.demo_app.catalog import OP_GROUP, catalogue, convert
from tests.demo_app.controller import Controller
from tests.demo_app.records import EventLog, tags_csv
from tests.demo_app.server import DemoServer, Runtime
from tests.demo_app.simulator import DemoTransport
from zk_rfid import InventoryConfig, InventoryData, TagMask, ValidationError, ZKReader


async def run(c, name, args=None, intent=None):
    accepted = await c.submit(name, args, intent)
    task = c.tasks.get(accepted["job_id"])
    if task:
        await task
    return c.jobs[accepted["job_id"]]


def test_catalogue_covers_every_public_native_method_and_valid_signature():
    public = {
        name
        for name, value in inspect.getmembers(ZKReader, inspect.isfunction)
        if not name.startswith("_")
    }
    assert public == set(OP_GROUP) | {"open", "close"}
    names = {x["name"] for x in catalogue()}
    assert names == set(OP_GROUP)
    for item in catalogue():
        args = {f["name"]: f["default"] for f in item["fields"]}
        converted = convert(item["name"], args)
        inspect.signature(getattr(ZKReader, item["name"])).bind(None, **converted)


def test_argument_conversion_is_typed_and_rejects_arbitrary_calls():
    result = convert(
        "inventory_once",
        {
            "config": {
                "data": "tid",
                "tid_word_count": 6,
                "mask": {"bank": 2, "bit_address": 0, "bit_length": 16, "data": "E280"},
            }
        },
    )
    assert isinstance(result["config"], InventoryConfig)
    assert result["config"].data is InventoryData.TID
    assert result["config"].mask == TagMask(2, 0, 16, bytes.fromhex("E280"))
    with pytest.raises(ValidationError):
        convert("__getattribute__", {})
    with pytest.raises(ValidationError):
        convert("set_power", {"power_dbm": 20, "unknown": 1})
    with pytest.raises(ValidationError):
        convert("inventory_once", {"config": {"bogus": 1}})


@pytest.mark.asyncio
async def test_simulation_config_and_inventory_use_real_codec_and_trace():
    log = EventLog()
    c = Controller(log)
    assert not c.reader
    try:
        assert (await run(c, "connect", {"simulate": True}))["state"] == "success"
        assert (await run(c, "get_reader_info"))["state"] == "success"
        assert (await run(c, "set_power", {"power_dbm": 17}))["state"] == "success"
        power = await run(c, "get_power")
        assert power["result"]["data"] == [17]
        out = await run(c, "inventory_once", {"config": {"data": "epc", "scan_time_100ms": 3}})
        assert out["result"]["reports"][0]["epc"] == "E20034120123456789000001"
        assert c.snapshot()["received_count"] == 1
        row = c.snapshot()["tags"][0]
        assert row["rssi_raw"] == 85 and row["rssi_dbm"] == -50
        exported = next(csv.DictReader(io.StringIO(tags_csv([row]))))
        assert exported["rssi_dbm"] == "-50.0" and exported["rssi_raw"] == "85"
        tag_event = next(e for e in log.events if e["kind"] == "tag")
        assert tag_event["report"]["rssi_source"] == "user_linear_raw_minus_135"
        assert exported["rssi_in_calibration_range"] == "True"
        assert any(e["kind"] == "frame" for e in log.events)
        first = await run(c, "get_reader_info")
        second = await run(c, "get_reader_info")
        assert first["result"] == second["result"]
        assert c.last_result["job_id"] == second["id"] != first["id"]
        await run(c, "disconnect")
        await run(c, "connect", {"simulate": True})
        assert not c.tags and c.received_count == 0
    finally:
        await c.shutdown()


@pytest.mark.asyncio
async def test_scenario_consumer_stop_restore_and_no_task_leak():
    c = Controller(EventLog())
    baseline = set(asyncio.all_tasks())
    try:
        await run(c, "connect", {"simulate": True})
        original = dict(c.transport.cfg)
        result = await run(
            c, "start_inventory", {"mode": "scenario", "config": {"q": 6, "phase": True}}
        )
        assert result["state"] == "success"
        await asyncio.sleep(0.02)
        assert c.received_count > 0
        result = await run(c, "stop_inventory")
        assert result["result"]["complete"]
        assert c.transport.cfg == original
        assert c.reader.state.value == "idle"
    finally:
        await c.shutdown()
    await asyncio.sleep(0)
    assert not [t for t in asyncio.all_tasks() - baseline if not t.done()]


@pytest.mark.asyncio
async def test_native_failure_partial_timeout_are_not_collapsed_to_boolean():
    c = Controller(EventLog())
    try:
        await run(c, "connect", {"simulate": True, "timeout": 0.03})
        for error, outcome, status in (
            ("failure", "failure", 0xF9),
            ("tag_error", "failure", 0xFC),
            ("partial", "partial", 0x13),
        ):
            await run(c, "inject", {"error": error})
            result = await run(c, "set_power", {"power_dbm": 20})
            assert result["state"] == outcome and result["result"]["status"] == status
        await run(c, "inject", {"error": "timeout"})
        result = await run(c, "set_power", {"power_dbm": 20})
        assert result["state"] == "unknown" and c.snapshot()["recovery_required"]
        await run(c, "disconnect")
        result = await run(c, "get_reader_info")
        assert result["state"] == "failure" and result["error"]["type"] == "StateError"
    finally:
        await c.shutdown()


@pytest.mark.asyncio
async def test_real_port_uncertainty_survives_visiting_simulator_without_opening_serial():
    # All transports here are byte peers; "real" only selects the UI recovery policy.
    c = Controller(EventLog(), transport_factory=lambda _: DemoTransport(1))
    try:
        await run(c, "connect", {"port": "TEST-PORT", "simulate": False, "timeout": 0.02})
        await run(c, "inject", {"error": "timeout"})
        await run(c, "get_reader_info")
        await run(c, "disconnect")
        assert c.uncertain_ports == {"TEST-PORT"}
        await run(c, "connect", {"simulate": True})
        await run(c, "disconnect")
        result = await run(c, "connect", {"port": "test-port", "simulate": False})
        assert result["state"] == "failure" and "clean" in result["error"]["message"]
        result = await run(
            c, "connect", {"port": "TEST-PORT", "simulate": False, "clean_boundary": True}
        )
        assert result["state"] == "success" and not c.uncertain_ports
    finally:
        await c.shutdown()


@pytest.mark.asyncio
async def test_direct_working_mode_can_be_stopped_and_disconnect_stops_raw_mode():
    c = Controller(EventLog())
    try:
        await run(c, "connect", {"simulate": True})
        assert (await run(c, "set_working_mode", {"mode": 1}))["state"] == "success"
        assert c.snapshot()["working_mode"] == 1 and c.session is None
        result = await run(c, "stop_inventory")
        assert result["state"] == "success" and c.snapshot()["working_mode"] == 0
        await run(c, "set_working_mode", {"mode": 2})
        await run(c, "disconnect")
        assert any(e["kind"] == "disconnect_mode_stop" for e in c.log.events)
    finally:
        await c.shutdown()


@pytest.mark.asyncio
async def test_tag_write_requires_explicit_intent_and_target_before_tx():
    c = Controller(EventLog())
    try:
        await run(c, "connect", {"simulate": True})
        before = sum(e["kind"] == "tx" for e in c.log.events)
        args = {"bank": 3, "word_address": 0, "data": "1234"}
        with pytest.raises(ValidationError):
            await c.submit("write_memory", args)
        with pytest.raises(ValidationError):
            await c.submit("write_memory", args, {"allow_tag_write": True})
        assert sum(e["kind"] == "tx" for e in c.log.events) == before
        with pytest.raises(ValidationError):
            await c.submit("get_reader_info", [])
        args["target"] = {"mask": {"bank": 2, "bit_address": 0, "bit_length": 16, "data": "E280"}}
        args["verify"] = True
        result = await run(c, "write_memory", args, {"allow_tag_write": True})
        assert result["result"]["confirmation"] == "read_back_verified"
        assert result["result"]["data"] == "1234"
        with pytest.raises(ValidationError):
            await c.submit(
                "kill_tag",
                {"kill_password": "12345678", "target": args["target"]},
                {"allow_tag_write": True},
            )
    finally:
        await c.shutdown()


def test_bounded_event_history_and_disk_export(tmp_path):
    log = EventLog(tmp_path / "test.jsonl", capacity=3)
    for i in range(6):
        log.append("sample", index=i)
    assert log.since(1)["missed"] == 2
    assert len(log.since(0)["events"]) == 3
    log.close()
    saved = [json.loads(line) for line in (tmp_path / "test.jsonl").read_text().splitlines()]
    assert len(saved) == 6
    exported = [json.loads(line) for line in log.export().splitlines()]
    assert exported[0]["bounded_history"] is True
    assert "E280" in tags_csv([{"epc": "E280", "count": 1}])


def test_http_static_api_origin_and_token_without_hardware(tmp_path):
    runtime = Runtime(EventLog(tmp_path / "http.jsonl"))
    server = DemoServer(runtime, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base) as r:
            assert b"RFID Test Console" in r.read()
            assert "frame-ancestors" in r.headers["Content-Security-Policy"]
        bootstrap = json.load(urllib.request.urlopen(base + "/api/bootstrap"))
        assert len(bootstrap["catalogue"]) == len(OP_GROUP)
        assert bootstrap["api_revision"] == 2
        assert bootstrap["features"]["live_tags"] is True
        body = json.dumps({"operation": "connect", "arguments": {"simulate": True}}).encode()
        request = urllib.request.Request(
            base + "/api/operation", body, headers={"Content-Type": "application/json"}
        )
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        assert error.value.code == 403
        request.add_header("X-Demo-Token", bootstrap["token"])
        request.add_header("Origin", "https://untrusted.example")
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        assert error.value.code == 403
        request.remove_header("Origin")
        with urllib.request.urlopen(request) as r:
            assert r.status == 202
        snapshot = runtime.snapshot()
        assert snapshot["connection"]["simulate"]
        assert not any(e["kind"] == "tx" for e in runtime.controller.log.events)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        runtime.close()
