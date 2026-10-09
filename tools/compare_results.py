"""Offline contract comparator; passes never imply RF/hardware equivalence."""

import argparse
import json
from pathlib import Path
from zk_rfid.compat.nation.mapping import power_dict, hex_epc
from zk_rfid.protocol import encode_command
from _common import emit


def compare(case):
    if case["equivalence"] in ("unverified", "unsupported", "approximate-with-conditions"):
        return {"id": case["id"], "status": "unverified", "reason": case["evidence"]}
    operation = case["operation"]
    if operation == "power_dictionary":
        actual = {str(k): v for k, v in power_dict(tuple(case["input"])).items()}
    elif operation == "epc_hex":
        actual = hex_epc(case["input"]).hex().upper()
    elif operation == "zk_command":
        v = case["input"]
        actual = encode_command(v["address"], v["command"], bytes.fromhex(v["data"])).hex().upper()
    else:
        return {
            "id": case["id"],
            "status": "unverified",
            "reason": "No comparator for this contract",
        }
    return {
        "id": case["id"],
        "status": "pass" if actual == case["expected"] else "fail",
        "actual": actual,
        "expected": case["expected"],
        "evidence": case["evidence"],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "manifest",
        nargs="?",
        default=str(Path(__file__).parents[1] / "compat/nation/mapping_cases.json"),
    )
    args = p.parse_args()
    cases = json.loads(Path(args.manifest).read_text(encoding="utf-8"))["cases"]
    results = [compare(c) for c in cases]
    for result in results:
        emit(result)
    emit(
        {
            "pass": sum(r["status"] == "pass" for r in results),
            "fail": sum(r["status"] == "fail" for r in results),
            "unverified": sum(r["status"] == "unverified" for r in results),
            "hardware_equivalence": False,
        }
    )
    if any(r["status"] == "fail" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
