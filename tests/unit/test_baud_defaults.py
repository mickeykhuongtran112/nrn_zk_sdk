"""Connection defaults must agree across Python examples and serial transport."""

import importlib.util
from pathlib import Path

from zk_rfid import SerialTransport


def load_example(name):
    path = Path(__file__).parents[2] / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_baud_and_explicit_override():
    assert SerialTransport("COM_TEST").baudrate == 115200
    assert SerialTransport("COM_TEST", 57600).baudrate == 57600
    common = load_example("_common")
    assert common.parser_for("reader_info").parse_args(["--port", "COM_TEST"]).baud == 115200
    scenario = load_example("inventory_scenario")
    assert scenario.parse_args(["--port", "COM_TEST"]).baud == 115200
