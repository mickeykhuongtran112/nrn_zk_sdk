"""Exercise the delivered file without an installed package or site-packages."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_copied_sdk_runs_in_isolated_python(tmp_path):
    shutil.copyfile(ROOT / "src/zk_rfid.py", tmp_path / "zk_rfid.py")
    shutil.copyfile(ROOT / "tests/runtime/runtime_checks.py", tmp_path / "runtime_checks.py")
    shutil.copyfile(ROOT / "fixtures/zk/documented/frames.json", tmp_path / "vectors.json")
    script = r"""
import asyncio
import importlib.abc
import inspect
import json
import logging
import pickle
import sys
from pathlib import Path
from typing import get_type_hints

sys.path.insert(0, str(Path.cwd()))

class NoOptionalImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "serial" or fullname.startswith("zk_rfid."):
            raise AssertionError("Unexpected runtime dependency: " + fullname)

guard = NoOptionalImports()
sys.meta_path.insert(0, guard)
root_handlers = list(logging.getLogger().handlers)
import zk_rfid as sdk
from runtime_checks import run_checks

assert Path(sdk.__file__).resolve() == Path("zk_rfid.py").resolve()
assert not hasattr(sdk, "__path__"), "Must be a module, not an embedded package"
assert not any(name.startswith("zk_rfid.") for name in sys.modules)
assert list(logging.getLogger().handlers) == root_handlers
assert "serial" not in sys.modules
assert len(sdk.__all__) == len(set(sdk.__all__))
assert all(hasattr(sdk, name) for name in sdk.__all__)
assert get_type_hints(sdk.ZKReader.start_inventory)["return"] is sdk.InventorySession
assert get_type_hints(sdk.InventoryConfig)["mask"] == sdk.TagMask | None
assert pickle.loads(pickle.dumps(sdk.InventoryConfig())) == sdk.InventoryConfig()
assert sdk.rssi_to_dbm(60) == -75 and sdk.rssi_to_dbm(110) == -25
assert inspect.getfile(sdk.NationAdapter) == sdk.__file__
transport = sdk.SerialTransport("COM13", 115200)
assert transport._serial is None
reader = sdk.ZKReader(transport)
assert reader.state is sdk.ReaderState.DISCONNECTED
result = asyncio.run(run_checks("vectors.json"))
assert result["leaked_tasks"] == 0

# Missing pyserial must fail only when opening the optional serial transport.
sys.meta_path.remove(guard)
sys.modules["serial"] = None
async def check_optional_serial():
    try:
        await transport.open()
    except sdk.TransportError as error:
        assert "pip install pyserial" in str(error)
    else:
        raise AssertionError("Expected the missing dependency error")
asyncio.run(check_optional_serial())
print(json.dumps(result))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", script],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    assert json.loads(result.stdout)["replayed_frames"] == 2000
