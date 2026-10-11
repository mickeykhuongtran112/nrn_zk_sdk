"""Approved GReaderTool 0.39 choices. Resolving a choice performs no device I/O."""

import json
from pathlib import Path

from zk_rfid import CustomRegion, Region, UnsupportedFeature, ValidationError, integer


def load_policy():
    data = json.loads(Path(__file__).with_name("rf_choices.json").read_text(encoding="utf-8"))
    if (
        data.get("selected_baseband_source") != "greader-0.39"
        or data.get("status") != "approved-application-policy"
    ):
        raise ValidationError("Expected the approved GReaderTool 0.39 policy")
    return data


def baseband_choice(speed):
    integer(speed, 0, 255, "speed")
    for row in load_policy()["greader_039_baseband_speeds"]:
        if row["nation_speed"] == speed:
            return row
    raise ValidationError("Unsupported GReaderTool 0.39 speed")


def region_choice(band_code):
    """Resolve the entire demo channel list; never expand a sparse selection."""
    integer(band_code, 0, 16, "band_code")
    row = next(row for row in load_policy()["bands"] if row["nation_band"] == band_code)
    if row["kind"] == "unsupported":
        raise UnsupportedFeature(f"NATION band {band_code}: {row['difference']}")
    if row["kind"] == "native":
        return Region(**row["region"])
    return CustomRegion(**row["centers"])
