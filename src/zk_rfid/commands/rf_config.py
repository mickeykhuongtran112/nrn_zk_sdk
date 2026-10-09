"""Native frequency tables and profile IDs. No cross-vendor numeric mapping."""

from ._common import Request, ack, exact, switch, u16, u8
from ..models import Region, boolean, integer
from ..errors import ProtocolError, ValidationError, UnverifiedFeature

# Band -> base kHz, spacing kHz, max index, per V2.25 pp.61-62.
REGIONS = {
    0: (840000, 2000, 60),
    1: (920125, 250, 19),
    2: (902750, 500, 49),
    3: (917100, 200, 31),
    4: (865100, 200, 14),
    6: (868000, 100, 6),
    8: (840125, 250, 19),
    9: (865700, 600, 3),
    12: (902000, 500, 52),
    16: (920250, 500, 9),
    17: (920750, 500, 13),
    18: (916300, 1200, 2),
    19: (919250, 500, 7),
    22: (920250, 500, 9),
    23: (920250, 500, 9),
    24: (920250, 500, 9),
    25: (865100, 600, 3),
    26: (916250, 500, 22),
    27: (918750, 500, 7),
    28: (916250, 500, 0),
    30: (922250, 500, 9),
    31: (916800, 1200, 3),
    32: (916250, 500, 22),
    33: (916200, 1200, 3),
    34: (915600, 200, 16),
    35: (918250, 500, 3),
}
# Discontinuous band formulas (21,29) have ambiguous second-segment indexing.
BAND_MAX = {**{k: v[2] for k, v in REGIONS.items()}, 21: 34, 29: 3}


def validate_region(region: Region) -> Region:
    integer(region.band, 0, 35, "band")
    if region.band not in BAND_MAX:
        raise ValidationError("Reserved or undocumented band")
    integer(region.min_channel, 0, BAND_MAX[region.band], "min_channel")
    integer(region.max_channel, region.min_channel, BAND_MAX[region.band], "max_channel")
    return region


def channel_frequency_khz(band: int, channel: int) -> int:
    validate_region(Region(band, channel, channel))
    if band not in REGIONS:
        raise UnverifiedFeature("Discontinuous region formula requires firmware confirmation")
    base, step, _ = REGIONS[band]
    return base + channel * step


def set_region(region: Region, *, persist=False, legacy=False) -> Request[None]:
    validate_region(region)
    boolean(persist, "persist")
    boolean(legacy, "legacy")
    if legacy:
        if region.band > 15 or not persist:
            raise ValidationError("Legacy region requires band <=15 and persistent setting")
        data = bytes(
            (
                ((region.band >> 2) << 6) | region.max_channel,
                ((region.band & 3) << 6) | region.min_channel,
            )
        )
    else:
        data = bytes((0 if persist else 1, region.band, region.max_channel, region.min_channel))
    return Request(0x22, data, ack, True)


def decode_region(data: bytes) -> Region:
    exact(data, 3)
    try:
        return validate_region(Region(data[0], data[2], data[1]))
    except ValidationError as error:
        raise ProtocolError(str(error)) from error


def get_region() -> Request[Region]:
    return Request(0x9E, decode=decode_region)


def profile(profile_id: int | None = None, *, persist=False, extended=True) -> Request[int]:
    boolean(persist, "persist")
    boolean(extended, "extended")
    if profile_id is not None:
        integer(profile_id, 0, 65535 if extended else 63, "profile_id")
    if extended:
        data = bytes((0 if profile_id is None else 1 if persist else 2,))
        data += (profile_id or 0).to_bytes(2, "big")
    else:
        data = bytes((0 if profile_id is None else 128 | (0 if persist else 64) | profile_id,))
    return Request(0x7F, data, u16 if extended else u8, profile_id is not None)


def drm(enabled: bool | None = None) -> Request[bool]:
    value = 0 if enabled is None else 128 | boolean(enabled, "enabled")
    return Request(0x90, bytes((value,)), switch, enabled is not None)
