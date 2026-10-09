import pytest

import zk_rfid as sdk
from zk_rfid import (
    PROFILES,
    QueryParameters,
    ReaderCapabilities,
    RealTimeConfig,
    Region,
    ScanParameters,
    TIDParameters,
    UnverifiedFeature,
    ValidationError,
)


@pytest.mark.parametrize(
    "cmd_request,hexdata",
    [
        (sdk.set_power((20, 21, 22, 23), ports=4), "94959697"),
        (sdk.set_power(30, ports=1, persist=True), "1e"),
        (sdk.set_write_power(25), "99"),
        (sdk.set_write_power(None), "00"),
        (sdk.write_retries(7), "87"),
        (sdk.set_antennas(0x8001, ports=16), "018001"),
        (sdk.set_antennas(0x80, ports=8, persist=True), "000080"),
        (sdk.set_antennas(5, ports=4), "85"),
        (sdk.set_antenna_check(False), "00"),
        (sdk.set_address(254), "fe"),
        (sdk.set_baudrate(115200), "06"),
        (sdk.set_scan_time(20), "14"),
        (sdk.set_interface("uart"), "01"),
        (sdk.heartbeat(2), "82"),
        (sdk.indicator(1, 2, 3), "010203"),
        (sdk.set_gpio(True, False), "01"),
        (sdk.set_buzzer(True), "01"),
        (sdk.set_region(Region(27, 0, 7)), "011b0700"),
        (sdk.set_region(Region(2, 0, 49), legacy=True, persist=True), "3180"),
        (sdk.profile(4124), "02101c"),
        (sdk.profile(), "000000"),
        (sdk.profile(3, extended=False), "c3"),
        (sdk.drm(True), "81"),
        (sdk.measure_return_loss(915000, 1, ports=1), "000df63800"),
        (sdk.return_loss_threshold(6), "86"),
        (sdk.set_buffer_length(62), "01"),
        (sdk.set_config(9, bytes((0x16, 255))), "010916ff"),
    ],
)
def test_command_tables(cmd_request, hexdata):
    assert cmd_request.data.hex() == hexdata


def test_typed_response_decoders():
    assert sdk.get_power(ports=4).decode(bytes((20, 21, 22, 23))) == (20, 21, 22, 23)
    assert sdk.get_write_power().decode(b"\x9e").power_dbm == 30
    assert sdk.decode_temperature(b"\0\x0a") == -10
    assert sdk.decode_temperature(b"\1\x25") == 37
    assert sdk.get_gpio().decode(b"\x21").output2
    assert sdk.get_region().decode(bytes((27, 7, 0))) == Region(27, 0, 7)
    assert sdk.profile().decode(bytes.fromhex("101c")) == 4124
    assert sdk.decode_counts(bytes.fromhex("00100020")).round_reads == 32
    assert sdk.get_buffer_length().decode(b"\1") == 62
    assert sdk.get_buffer_count().decode(b"\x01\x00") == 256


def test_real_time_set_variable_get_fixed_layout():
    assert sdk.set_real_time(RealTimeConfig()).data == bytes((0, 3, 0, 4, 0))
    data = (
        bytes((1, 0, 3, 7, 0x46, 1, 2, 0, 0, 16))
        + bytes.fromhex("e280")
        + bytes(30)
        + bytes((0, 6))
    )
    cfg = sdk.decode_working_mode(data)
    assert cfg.config.mask.data == bytes.fromhex("e280")
    assert cfg.config.tid_word_count == 6 and cfg.mode == 1
    assert cfg.config.special_strategy


def test_extended_codecs():
    assert sdk.encode_scan(ScanParameters(3, 0, 5)) == bytes((3, 0, 5))
    assert sdk.encode_query(QueryParameters(6, 254, True)) == bytes((22, 254))
    assert sdk.encode_tid(TIDParameters(3, 15)) == bytes((3, 15))
    assert sdk.encode_profiles((103, 241, 4124)).hex() == "006700f1101c"
    for num, data in (
        (7, bytes((3, 0, 5))),
        (8, b"\1"),
        (9, b"\x16\xfe"),
        (10, b"\3\x0f"),
        (11, bytes.fromhex("01002008AB")),
        (31, bytes.fromhex("006700f1101c")),
    ):
        assert sdk.get_config(num).decode(data) is not None


def test_errata_gated():
    with pytest.raises(UnverifiedFeature):
        sdk.set_config(25, bytes((15, 1, 3, 2, 3, 0)))
    assert sdk.set_config(25, bytes((15, 1, 3, 2, 3, 0)), confirmed_length=6).command == 0xEA
    assert sdk.set_config(29, bytes((1, 1, 1, 2, 3)), confirmed_length=5).command == 0xEA
    with pytest.raises(UnverifiedFeature):
        sdk.decode_buffer(b"\0", ports=16)
    assert sdk.decode_buffer(b"\0", ports=16, antenna_bytes=2) == []


def test_ranges_and_profile_units():
    assert len(PROFILES) == 54
    assert PROFILES[4124].encoding == "BPSK2"
    assert PROFILES[146].blf_khz == 250 and PROFILES[146].tari_us == 20
    assert sdk.channel_frequency_khz(27, 7) == 922250
    with pytest.raises(UnverifiedFeature):
        sdk.channel_frequency_khz(21, 10)
    with pytest.raises(ValidationError):
        sdk.set_power(True, ports=1)
    with pytest.raises(ValidationError):
        ReaderCapabilities(antenna_ports=2)
