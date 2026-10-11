"""JSON contract shared by the browser bridge and the Python test console."""

import importlib.util
from pathlib import Path

import pytest

from tests.demo_app.catalog import catalogue, convert
from zk_rfid import InventoryConfig, InventoryData, MemoryBank, TagTarget, ValidationError

spec = importlib.util.spec_from_file_location(
    "web_bridge_test", Path(__file__).resolve().parents[2] / "web" / "zk_browser.py"
)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def test_browser_accepts_the_same_public_arguments_as_the_python_console():
    operations = catalogue()
    assert bridge.METHODS == {entry["name"] for entry in operations}
    for entry in operations:
        values = {field["name"]: field["default"] for field in entry["fields"]}
        assert bridge.arguments(entry["name"], values) == convert(entry["name"], values)


def test_nested_bytes_enums_and_targets_reach_native_types():
    config = {
        "data": "mix",
        "memory_bank": 3,
        "access_password": "01234567",
        "mask": {"bank": 2, "bit_address": 32, "bit_length": 16, "data": "E280"},
    }
    parsed = bridge.arguments("inventory_once", {"config": config})["config"]
    assert isinstance(parsed, InventoryConfig)
    assert parsed.data is InventoryData.MIX
    assert parsed.memory_bank is MemoryBank.USER
    assert parsed.access_password == bytes.fromhex("01234567")
    assert parsed.mask.data == bytes.fromhex("E280")
    assert bridge.plain(parsed)["mask"] == config["mask"]
    assert bridge.arguments("write_epc", {"epc": "12345678", "target": {"epc": "ABCD"}}) == {
        "epc": bytes.fromhex("12345678"),
        "target": TagTarget(epc=bytes.fromhex("ABCD")),
    }


def test_lifecycle_private_methods_and_invalid_hex_are_not_forwarded():
    for operation in ("open", "close", "_execute", "__getattribute__"):
        with pytest.raises(ValidationError):
            bridge.arguments(operation, {})
    with pytest.raises(ValidationError):
        bridge.arguments("write_epc", {"epc": "not hex", "target": {"epc": "ABCD"}})
    with pytest.raises(TypeError):
        bridge.arguments("get_power", {"unexpected": True})
