"""Keep the review catalogue complete and RF proposals internally consistent."""

import copy
import json

import pytest

from zk_rfid import ValidationError

from tools.check_nation_mapping import (
    FOLDER,
    check_choices,
    check_coverage,
    check_rf_tables,
    main,
    proposed_calls,
)


def choices():
    return json.loads((FOLDER / "rf_choices.json").read_text(encoding="utf-8"))


def test_entire_pinned_public_api_and_command_inventory_is_documented():
    result = check_coverage((FOLDER / "api_map.md").read_text(encoding="utf-8"))
    assert result == {"public_callables": 64, "command_constants": 30}


def test_missing_api_row_is_detected():
    text = (FOLDER / "api_map.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="NRNReader.configure_baseband"):
        check_coverage(text.replace("`NRNReader.configure_baseband`", "`missing`"))


def test_review_choices_validate_and_do_not_execute():
    data = choices()
    check_choices(data)
    check_rf_tables(data, (FOLDER / "rf_mapping.md").read_text(encoding="utf-8"))
    calls = list(proposed_calls(data, baseband_source="nextwaves"))
    taiwan = next(r for r in calls if r.get("nation_band") == 6)
    assert taiwan["operation"] == "set_custom_region"
    assert taiwan["arguments"] == {
        "start_frequency_khz": 922250,
        "channel_count": 12,
        "spacing_khz": 500,
        "persist": False,
    }
    assert next(r for r in calls if r.get("nation_band") == 2)["operation"] is None
    assert next(r for r in calls if r.get("nation_speed") == 255)["operation"] == "get_profile"


def test_speed_four_requires_a_source_dialect():
    data = choices()
    legacy = list(proposed_calls(data, baseband_source="nextwaves"))
    demo = list(proposed_calls(data, baseband_source="greader-0.39"))
    assert next(r for r in legacy if r.get("nation_speed") == 4)["arguments"]["profile_id"] == 141
    assert next(r for r in demo if r.get("nation_speed") == 4)["arguments"]["profile_id"] == 123
    with pytest.raises(ValueError, match="source explicitly"):
        list(proposed_calls(data, baseband_source=None))


def test_cli_show_requires_explicit_dialect(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["check_nation_mapping.py", "--show"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "--show requires --baseband-source" in capsys.readouterr().err


def test_demo_channel_facts_do_not_silently_drop_or_round_channels():
    data = choices()
    bands = {r["nation_band"]: r for r in data["bands"]}
    # FrmBaseDialog.InitFrequency in GReaderTool 0.39.0.0, reviewed independently.
    assert bands[7]["centers"] == {
        "start_frequency_khz": 923125,
        "channel_count": 9,
        "spacing_khz": 250,
    }
    assert bands[4]["source_segments"] == [
        {"start_frequency_khz": 865700, "channel_count": 5, "spacing_khz": 600}
    ]
    assert bands[8]["source_segments"] == [
        {"start_frequency_khz": 866600, "channel_count": 5, "spacing_khz": 200}
    ]
    calls = list(proposed_calls(data, baseband_source="greader-0.39"))
    for code in (2, 4, 8, 9, 10, 16):
        assert next(r for r in calls if r.get("nation_band") == code)["operation"] is None


def test_valid_custom_grid_that_drops_source_channels_is_rejected():
    data = choices()
    # The earlier 5 x 500 kHz draft is encodable but loses four of the nine ID channels.
    data["bands"][7]["centers"].update(channel_count=5, spacing_khz=500)
    with pytest.raises(ValueError, match="entire source center list"):
        check_choices(data)


def test_valid_native_subset_cannot_replace_full_demo_etsi_band():
    data = choices()
    data["bands"][4].update(
        kind="native",
        region={"band": 9, "min_channel": 0, "max_channel": 3},
        centers={"start_frequency_khz": 865700, "channel_count": 4, "spacing_khz": 600},
    )
    with pytest.raises(ValueError, match="entire source center list"):
        check_choices(data)


def test_unsupported_band_must_stay_visible_in_docs():
    text = (FOLDER / "rf_mapping.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported frequency row"):
        check_rf_tables(choices(), text.replace("No exact mapping", "Custom"))


@pytest.mark.parametrize(
    "failure", ["spacing", "native_index", "encoding", "auto_apply", "envelope"]
)
def test_invalid_rf_review_choices_are_detected(failure):
    data = copy.deepcopy(choices())
    if failure == "spacing":
        data["bands"][6]["centers"]["spacing_khz"] = 200
    elif failure == "native_index":
        data["bands"][0]["region"]["min_channel"] = 0
    elif failure == "encoding":
        data["baseband_speeds"][1]["zk_profile_id"] = 103
    elif failure == "auto_apply":
        data["runtime_applied"] = False
    else:
        data["bands"][6]["centers"]["start_frequency_khz"] = 960000
    with pytest.raises((ValueError, ValidationError)):
        check_choices(data)


def test_documented_profile_must_follow_review_json():
    data = choices()
    data["baseband_speeds"][1]["zk_profile_id"] = 244
    with pytest.raises(ValueError, match="Update rf_mapping"):
        check_rf_tables(data, (FOLDER / "rf_mapping.md").read_text(encoding="utf-8"))
