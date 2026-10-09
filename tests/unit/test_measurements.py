import math
import pytest
from zk_rfid import phase_to_degrees, phase_to_radians, rssi_to_dbm, ValidationError


def test_vendor_phase_conversion_wrap_and_full_scaled_word():
    assert phase_to_degrees(0) == 0
    assert phase_to_degrees(2068) == pytest.approx(179.916)
    assert phase_to_degrees(2069) == pytest.approx(0.003)
    assert phase_to_degrees(0x0E8F) == pytest.approx(144.249)
    assert phase_to_degrees(0x0E8F, wrap=False) == pytest.approx(324.249)
    assert phase_to_radians(0x0E8F) == pytest.approx(144.249 * math.pi / 180)
    assert phase_to_radians(0x0E8F, wrap=False) == pytest.approx(324.249 * math.pi / 180)
    assert 0 <= phase_to_degrees(65535) < 180


@pytest.mark.parametrize("raw", [-1, 65536, True, 3.5, "018F", None])
def test_invalid_phase_code_is_rejected(raw):
    with pytest.raises(ValidationError):
        phase_to_degrees(raw)


def test_wrap_option_is_explicit_boolean():
    with pytest.raises(ValidationError):
        phase_to_radians(399, wrap=180)


@pytest.mark.parametrize(
    "raw,dbm", [(0, -135), (59, -76), (60, -75), (85, -50), (110, -25), (111, -24), (255, 120)]
)
def test_user_rssi_anchors_and_unclamped_extrapolation(raw, dbm):
    assert rssi_to_dbm(raw) == dbm


@pytest.mark.parametrize("raw", [-1, 256, True, 85.5, "85", None])
def test_rssi_requires_unsigned_byte(raw):
    with pytest.raises(ValidationError):
        rssi_to_dbm(raw)
