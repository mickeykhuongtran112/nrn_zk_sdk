import pytest
from zk_rfid import TagReport, UnverifiedFeature, ValidationError, InventoryConfig
from zk_rfid.commands.inventory import decode_answer
from zk_rfid.compat.nation.mapping import RFMapping, hex_epc, power_dict, tag_dict


def test_measurements_not_fabricated():
    value = tag_dict(TagReport(epc=b"\0\1", rssi_raw=85))
    assert value["epc"] == "0001" and value["rssi_raw"] == 85
    assert "rssi" not in value and "phase" not in value and "pc" not in value
    absent = tag_dict(TagReport())
    assert absent["rssi_dbm"] is absent["rssi_source"] is None


def test_adapter_preserves_user_rssi_mapping_provenance():
    report = decode_answer(bytes.fromhex("010102ABCD55"), InventoryConfig(), ports=1)[0]
    value = tag_dict(report)
    assert value["rssi_raw"] == 85 and value["rssi_dbm"] == -50
    assert value["rssi_source"] == "user_linear_raw_minus_135"
    assert value["rssi_in_calibration_range"] is True


def test_power_mapping():
    assert power_dict((10, 20)) == {1: 10, 2: 20}


def test_profile_requires_explicit_evidence():
    with pytest.raises(UnverifiedFeature):
        RFMapping(1, 1, "").require(1)
    with pytest.raises(UnverifiedFeature):
        RFMapping(1, 146, "lab", True).require(2)
    assert RFMapping(1, 146, "caller supplied bench measurement", True).require(1) == 146


def test_epc_lossless_and_word_aligned():
    assert hex_epc("0000aBcD") == bytes.fromhex("0000ABCD")
    with pytest.raises(ValidationError):
        hex_epc("00 01")
