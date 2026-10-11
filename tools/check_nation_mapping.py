"""Validate approved mappings and retained alternatives without device I/O."""

import argparse
import ast
import json
import re
from pathlib import Path

from zk_rfid import PROFILES, CustomRegion, Region, channel_frequency_khz, validate_region

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "mapping/nation_to_zk"
SPEED_SOURCES = {
    "nextwaves": "baseband_speeds",
    "greader-0.39": "greader_039_baseband_speeds",
}


def reference_inventory():
    """Read source with AST; importing the reference would create its logger."""
    tree = ast.parse((ROOT / "compat/nation/nrn.py").read_text(encoding="utf-8"))
    functions, commands = set(), set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            functions.add(node.name)
        if not isinstance(node, ast.ClassDef):
            continue
        for member in node.body:
            if isinstance(member, ast.FunctionDef) and (
                not member.name.startswith("_") or member.name == "__init__"
            ):
                functions.add(f"{node.name}.{member.name}")
            if node.name == "MID" and isinstance(member, ast.Assign):
                commands.update(
                    f"MID.{target.id}" for target in member.targets if isinstance(target, ast.Name)
                )
    return functions, commands


def check_coverage(text):
    functions, commands = reference_inventory()
    rows = re.findall(r"^\| `([^`]+)` \|", text, re.M)
    expected = functions | commands
    missing = expected - set(rows)
    extra = set(rows) - expected
    duplicates = sorted(name for name in expected if rows.count(name) > 1)
    if missing or extra or duplicates:
        raise ValueError(
            f"API map mismatch: missing={sorted(missing)}, extra={sorted(extra)}, "
            f"duplicates={duplicates}"
        )
    return {"public_callables": len(functions), "command_constants": len(commands)}


def check_choices(choices):
    if choices["schema_version"] != 2:
        raise ValueError("RF worksheet requires explicit baseband dialects (schema 2)")
    if (
        choices["runtime_applied"] is not True
        or choices["status"] != "approved-application-policy"
        or choices.get("selected_baseband_source") != "greader-0.39"
        or choices.get("antenna", {}).get("persist") is not True
    ):
        raise ValueError("Expected approved GReaderTool policy with saved antenna configuration")
    speeds = choices["baseband_speeds"]
    demo_speeds = choices["greader_039_baseband_speeds"]
    presets = choices["profile_presets"]
    bands = choices["bands"]
    for rows, key, expected in (
        (speeds, "nation_speed", {0, 1, 2, 3, 4, 255}),
        (demo_speeds, "nation_speed", {0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 255}),
        (presets, "nation_profile", {0, 1, 2}),
        (bands, "nation_band", set(range(17))),
    ):
        if {r[key] for r in rows} != expected or len(rows) != len(expected):
            raise ValueError(f"Missing or duplicate {key} choices")
    for row in speeds + demo_speeds + presets:
        profile = row["zk_profile_id"]
        if profile is None:
            if row.get("nation_speed") != 255:
                raise ValueError("Only automatic speed may keep the current profile")
        else:
            if type(profile) is not int or profile not in PROFILES:
                raise ValueError(f"Unknown native profile: {profile}")
            if row.get("encoding") and PROFILES[profile].encoding != row["encoding"]:
                raise ValueError(
                    "Baseband proposal must preserve encoding or revise its stated policy"
                )
        if not row["difference"].strip():
            raise ValueError("Every RF choice needs its differences recorded")
    for row in bands:
        if not row["difference"].strip():
            raise ValueError("Every band needs its differences recorded")
        source_centers = []
        for part in row["source_segments"]:
            start, count, step = (
                part["start_frequency_khz"],
                part["channel_count"],
                part["spacing_khz"],
            )
            if not all(type(v) is int for v in (start, count, step)) or (
                start <= 0 or count <= 0 or step < 0 or (count > 1 and step == 0)
            ):
                raise ValueError("Invalid source center list")
            source_centers.extend(start + n * step for n in range(count))
        if not source_centers or source_centers != sorted(set(source_centers)):
            raise ValueError("Source centers must be unique and ascending")
        if row["kind"] == "unsupported":
            if row["centers"] is not None or row["region"] is not None:
                raise ValueError("Unsupported band must not contain an executable plan")
            continue
        plan = row["centers"]
        if row["kind"] == "custom":
            CustomRegion(**plan)
            if row["region"] is not None:
                raise ValueError("Custom plan must not carry a native band")
        elif row["kind"] == "native":
            region = validate_region(Region(**row["region"]))
            actual = [
                channel_frequency_khz(region.band, n)
                for n in range(region.min_channel, region.max_channel + 1)
            ]
            expected = [
                plan["start_frequency_khz"] + n * plan["spacing_khz"]
                for n in range(plan["channel_count"])
            ]
            if actual != expected:
                raise ValueError(
                    f"Native channel list mismatch for NATION band {row['nation_band']}"
                )
        else:
            raise ValueError(f"Unknown plan kind: {row['kind']}")
        candidate = [
            plan["start_frequency_khz"] + n * plan["spacing_khz"]
            for n in range(plan["channel_count"])
        ]
        if candidate != source_centers:
            raise ValueError("Proposed channel plan must preserve the entire source center list")
        first = plan["start_frequency_khz"]
        last = first + (plan["channel_count"] - 1) * plan["spacing_khz"]
        low, high = row["envelope_khz"]
        if not low <= first <= last <= high:
            raise ValueError(f"Candidate leaves NATION label envelope: {row['nation_band']}")


def check_rf_tables(choices, text):
    """Catch stale displayed IDs/centers when the review JSON is edited."""
    baseband, remainder = text.split("## Profile buttons", 1)
    legacy, demo = baseband.split("### GReaderTool 0.39", 1)
    frequency = remainder.split("## Frequency", 1)[1]
    for rows, section in (
        (choices["baseband_speeds"], legacy),
        (choices["greader_039_baseband_speeds"], demo),
    ):
        for row in rows:
            cells = re.search(rf"^\| {row['nation_speed']} \| (.+)$", section, re.M)
            if not cells:
                raise ValueError("Missing baseband documentation row")
            shown = cells[1].split("|")[1].strip()
            expected = (
                str(row["zk_profile_id"]) if row["zk_profile_id"] is not None else "Keep current"
            )
            if shown != expected:
                raise ValueError("Update rf_mapping.md after changing a proposed profile")
    for row in choices["bands"]:
        match = re.search(rf"^\| {row['nation_band']} [^|]+\| (.+)$", frequency, re.M)
        if not match:
            raise ValueError("Missing frequency documentation row")
        if row["kind"] == "unsupported":
            if "No exact mapping" not in match[1]:
                raise ValueError("Unsupported frequency row must show No exact mapping")
            continue
        plan = row["centers"]
        first = plan["start_frequency_khz"]
        last = first + (plan["channel_count"] - 1) * plan["spacing_khz"]
        if f"{first / 1000:.3f}–{last / 1000:.3f}" not in match[1]:
            raise ValueError("Update rf_mapping.md after changing a channel plan")
        if f"{plan['channel_count']} / {plan['spacing_khz']}" not in match[1]:
            raise ValueError("Update rf_mapping.md count/spacing")


def proposed_calls(choices, *, baseband_source):
    if baseband_source not in SPEED_SOURCES:
        raise ValueError("Select nextwaves or greader-0.39 baseband source explicitly")
    for row in choices[SPEED_SOURCES[baseband_source]]:
        profile = row["zk_profile_id"]
        yield {
            "baseband_source": baseband_source,
            "nation_speed": row["nation_speed"],
            "operation": "set_profile" if profile is not None else "get_profile",
            "arguments": {"profile_id": profile, "persist": False} if profile is not None else {},
            "difference": row["difference"],
        }
    for row in choices["bands"]:
        if row["kind"] == "unsupported":
            arguments, operation = {}, None
        elif row["kind"] == "native":
            arguments, operation = {"region": row["region"], "persist": False}, "set_region"
        else:
            arguments, operation = {**row["centers"], "persist": False}, "set_custom_region"
        yield {
            "nation_band": row["nation_band"],
            "operation": operation,
            "arguments": arguments,
            "difference": row["difference"],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--show", action="store_true", help="Print review-only native calls; no I/O"
    )
    parser.add_argument("--baseband-source", choices=tuple(SPEED_SOURCES))
    args = parser.parse_args()
    if args.show and args.baseband_source is None:
        parser.error("--show requires --baseband-source; speed IDs differ between sources")
    coverage = check_coverage((FOLDER / "api_map.md").read_text(encoding="utf-8"))
    choices = json.loads((FOLDER / "rf_choices.json").read_text(encoding="utf-8"))
    check_choices(choices)
    check_rf_tables(choices, (FOLDER / "rf_mapping.md").read_text(encoding="utf-8"))
    if args.show:
        print(
            json.dumps(
                list(proposed_calls(choices, baseband_source=args.baseband_source)), indent=2
            )
        )
    print(
        json.dumps(
            {
                **coverage,
                "rf_choices": "valid approved application policy",
                "hardware_equivalence": False,
            }
        )
    )


if __name__ == "__main__":
    main()
