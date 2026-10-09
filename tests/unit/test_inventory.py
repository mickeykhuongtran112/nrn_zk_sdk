from dataclasses import replace

import pytest

from zk_rfid import (
    InventoryConfig,
    InventoryData,
    MixDecoder,
    ProtocolError,
    TagMask,
    UnverifiedFeature,
    build_inventory,
    decode_answer,
    decode_heartbeat,
    decode_statistics,
    decode_stream,
    inventory_epc,
)


def test_independent_inventory_vectors():
    cfg = InventoryConfig(scan_time_100ms=3)
    assert build_inventory(cfg, ports=1).data.hex() == "0400008003"
    masked = replace(cfg, mask=TagMask(2, 0, 16, bytes.fromhex("e280")))
    assert build_inventory(masked, ports=1).data.hex() == "040002000010e280008003"
    mix = replace(cfg, data=InventoryData.MIX, memory_bank=1, word_address=1)
    assert build_inventory(mix, ports=1).data.hex() == "04000100010100000000008003"


def test_fastid_phase_and_rssi_provenance():
    epc, tid = b"\xde\xad", bytes(range(12))
    data = b"\x01\x01\xce" + epc + tid + b"\x60" + bytes.fromhex("000100020ddf60")
    report = decode_answer(data, InventoryConfig(data=InventoryData.FAST_ID), ports=1)[0]
    assert (report.epc, report.tid) == (epc, tid)
    assert report.phase_raw == b"\0\x01\0\x02"
    assert (report.phase_begin_raw, report.phase_end_raw) == (1, 2)
    assert report.phase_begin_degrees == pytest.approx(0.087)
    assert report.phase_end_degrees == pytest.approx(0.174)
    assert report.frequency_khz == 909152
    assert report.rssi_dbm == -39 and report.phase_radians is None
    assert report.rssi_source == "user_linear_raw_minus_135"
    assert report.rssi_in_calibration_range is True


@pytest.mark.parametrize("mode", ["answer", "fastid", "tid", "mix", "scenario"])
def test_phase_words_units_and_unsigned_rssi_across_report_formats(mode):
    # User example 018F018D = BE16 399/397. Source: Ex10 V6.8 Form1.cs.
    trailer = bytes.fromhex("018F018D0E06D2")
    value = bytes.fromhex("ABCD")
    cfg = InventoryConfig()
    flags = 0x42
    if mode == "fastid":
        value += bytes(range(12))
        flags = 0xCE
        cfg = replace(cfg, data=InventoryData.FAST_ID)
    if mode == "tid":
        cfg = replace(cfg, data=InventoryData.TID, tid_word_count=1)
    record = bytes((flags,)) + value + b"\xc8" + trailer
    if mode == "scenario":
        report = decode_stream(b"\1" + record, ports=1)
    elif mode == "mix":
        decoder = MixDecoder(replace(cfg, data=InventoryData.MIX), 1)
        decoder.feed(b"\1\1\0" + record)
        report = decoder.feed(bytes.fromhex("01018102000150"))[0]
    else:
        report = decode_answer(b"\1\1" + record, cfg, ports=1)[0]
    assert (report.phase_begin_raw, report.phase_end_raw) == (399, 397)
    assert report.phase_begin_degrees == pytest.approx(34.713)
    assert report.phase_end_degrees == pytest.approx(34.539)
    assert report.phase_begin_radians == pytest.approx(0.605856143259)
    assert report.phase_end_radians == pytest.approx(0.602819270361)
    assert report.phase_conversion == "ex10_v6_8_demo_0.087deg_mod180"
    assert report.phase_raw.hex() == "018f018d"
    assert report.rssi_raw == 200 and report.rssi_dbm == 65  # Raw stays unsigned.
    assert report.rssi_source == "user_linear_raw_minus_135"
    assert report.rssi_in_calibration_range is False  # Extrapolation is explicit.


def test_absent_phase_stays_absent():
    report = decode_answer(bytes.fromhex("010102ABCD6E"), InventoryConfig(), ports=1)[0]
    assert report.rssi_raw == 110
    assert report.rssi_dbm == -25 and report.rssi_in_calibration_range is True
    assert report.phase_raw is report.phase_begin_raw is report.phase_end_raw is None
    assert report.phase_begin_degrees is report.phase_end_radians is report.phase_conversion is None


def test_realtime_and_buffer_use_same_user_rssi_mapping():
    from zk_rfid import decode_buffer

    realtime = decode_stream(bytes.fromhex("0102ABCD3C"), ports=1, scenario=False)
    buffered = decode_buffer(bytes.fromhex("010102ABCD5503"), ports=1)[0]
    assert realtime.rssi_raw == 60 and realtime.rssi_dbm == -75
    assert buffered.rssi_raw == 85 and buffered.rssi_dbm == -50
    assert buffered.read_count == 3
    for report in (realtime, buffered):
        assert report.rssi_source == "user_linear_raw_minus_135"
        assert report.rssi_in_calibration_range is True


def test_tid_and_multi_antenna():
    cfg = InventoryConfig(data=InventoryData.TID, tid_word_count=2)
    r = decode_answer(bytes.fromhex("050104E280000061"), cfg, ports=4)[0]
    assert r.epc is None and r.tid == bytes.fromhex("E2800000")
    assert r.antenna is None and r.antenna_mask == 5
    r16 = decode_stream(bytes.fromhex("0F04E280000061"), ports=16, tid_words=2)
    assert r16.antenna == 16


def test_mix_pair_across_frames_wrap_and_missing():
    cfg = InventoryConfig(data=InventoryData.MIX)
    decoder = MixDecoder(cfg, 1)
    assert decoder.feed(bytes.fromhex("01017F04DEADBEEF50")) == []
    out = decoder.feed(bytes.fromhex("01018002000151"))
    assert out[0].memory_data == b"\0\x01"
    decoder.feed(bytes.fromhex("01010102ABCD60"))
    assert decoder.flush()[0].epc == bytes.fromhex("ABCD")
    assert decoder.missing_memory == 1


def test_mix_orphan_and_different_antenna_never_pair():
    decoder = MixDecoder(InventoryConfig(data=InventoryData.MIX), 4)
    decoder.feed(bytes.fromhex("01010002ABCD60"))
    out = decoder.feed(bytes.fromhex("02018102000160"))
    assert out[0].memory_data is None
    assert decoder.orphan_memory == 1


@pytest.mark.parametrize("data", ["01010", "010104AB", "010182ABCD60", "010102ABCD6000"])
def test_malformed_reports(data):
    if len(data) % 2:
        data = data[:-1]
    with pytest.raises(ProtocolError):
        decode_answer(bytes.fromhex(data), InventoryConfig(), ports=1)


def test_stats_and_heartbeat():
    s = decode_statistics(bytes.fromhex("0103E8000003E8"))
    assert s.total_reads == s.reads_per_second == 1000
    h = decode_heartbeat(bytes.fromhex("FFFFFFFF0100000001"), ports=1)
    assert h.packet_number == 0xFFFFFFFF and h.total_reads == 1


def test_mix_ambiguous_large_response_is_gated():
    with pytest.raises(UnverifiedFeature):
        build_inventory(InventoryConfig(data=InventoryData.MIX, word_count=32), ports=1)


def test_epc_matching_bit_fields():
    assert inventory_epc(b"\xa0", 3, 7, exclude=True).data.hex() == "0100030007a0"
