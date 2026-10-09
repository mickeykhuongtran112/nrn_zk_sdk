import ast
from pathlib import Path
import pytest
from tests.runtime.runtime_checks import run_checks

ROOT = Path(__file__).parents[2]


@pytest.mark.asyncio
@pytest.mark.runtime
async def test_shared_runtime_checks():
    result = await run_checks(ROOT / "fixtures/zk/documented/frames.json")
    assert result["replayed_frames"] == 2000 and result["leaked_tasks"] == 0


def test_core_does_not_import_optional_or_blocking_runtime():
    forbidden = {"serial", "threading", "multiprocessing", "os", "subprocess"}
    for path in (ROOT / "src/zk_rfid").rglob("*.py"):
        if "transports" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not forbidden.intersection(n.name.split(".")[0] for n in node.names), path
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                assert (node.module or "").split(".")[0] not in forbidden, path
