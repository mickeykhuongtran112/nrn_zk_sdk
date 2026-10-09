"""Native Ex10 RF profiles transcribed from V2.25 pp.85-86.

These are documented physical parameters, not RF equivalence with NATION.
No profile is selected automatically and availability is firmware-dependent.
"""

from dataclasses import dataclass
from .errors import UnverifiedFeature


@dataclass(frozen=True)
class RFProfile:
    id: int
    modulation: str
    pie: float
    tari_us: float
    blf_khz: int
    encoding: str
    evidence: str = "V2.25 pp.85-86; hardware unverified"


PROFILES = {
    1: RFProfile(1, "PR_ASK", 2.0, 7.5, 640, "Miller2"),
    3: RFProfile(3, "PR_ASK", 2.0, 20.0, 320, "Miller2"),
    5: RFProfile(5, "PR_ASK", 2.0, 20.0, 320, "Miller4"),
    7: RFProfile(7, "PR_ASK", 2.0, 20.0, 250, "Miller4"),
    11: RFProfile(11, "PR_ASK", 2.0, 7.5, 640, "FM0"),
    12: RFProfile(12, "PR_ASK", 2.0, 15.0, 320, "Miller2"),
    13: RFProfile(13, "PR_ASK", 2.0, 20.0, 160, "Miller8"),
    15: RFProfile(15, "PR_ASK", 2.0, 7.5, 640, "Miller4"),
    102: RFProfile(102, "PR_ASK", 2.0, 7.5, 640, "FM0"),
    103: RFProfile(103, "DSB", 1.5, 6.25, 640, "FM0"),
    104: RFProfile(104, "DSB", 1.5, 6.25, 320, "FM0"),
    120: RFProfile(120, "DSB", 1.5, 6.25, 640, "Miller2"),
    123: RFProfile(123, "PR_ASK", 2.0, 20.0, 320, "Miller2"),
    124: RFProfile(124, "PR_ASK", 2.0, 7.5, 640, "Miller2"),
    125: RFProfile(125, "PR_ASK", 2.0, 15.0, 320, "Miller2"),
    126: RFProfile(126, "PR_ASK", 1.5, 12.5, 320, "Miller2"),
    141: RFProfile(141, "PR_ASK", 2.0, 20.0, 320, "Miller4"),
    146: RFProfile(146, "PR_ASK", 2.0, 20.0, 250, "Miller4"),
    147: RFProfile(147, "PR_ASK", 2.0, 7.5, 640, "Miller4"),
    148: RFProfile(148, "PR_ASK", 1.5, 7.5, 640, "Miller4"),
    185: RFProfile(185, "PR_ASK", 2.0, 20.0, 160, "Miller8"),
    202: RFProfile(202, "PR_ASK", 2.0, 15.0, 426, "FM0"),
    203: RFProfile(203, "PR_ASK", 1.5, 12.5, 426, "FM0"),
    205: RFProfile(205, "PR_ASK", 2.0, 20.0, 50, "FM0"),
    222: RFProfile(222, "PR_ASK", 2.0, 20.0, 320, "Miller2"),
    223: RFProfile(223, "PR_ASK", 2.0, 15.0, 320, "Miller2"),
    224: RFProfile(224, "PR_ASK", 1.5, 12.5, 320, "Miller2"),
    225: RFProfile(225, "PR_ASK", 2.0, 15.0, 426, "Miller2"),
    226: RFProfile(226, "PR_ASK", 1.5, 12.5, 426, "Miller2"),
    241: RFProfile(241, "PR_ASK", 2.0, 20.0, 320, "Miller4"),
    244: RFProfile(244, "PR_ASK", 2.0, 20.0, 250, "Miller4"),
    285: RFProfile(285, "PR_ASK", 2.0, 20.0, 160, "Miller8"),
    302: RFProfile(302, "PR_ASK", 2.0, 7.5, 640, "FM0"),
    323: RFProfile(323, "PR_ASK", 2.0, 7.5, 640, "Miller2"),
    324: RFProfile(324, "PR_ASK", 2.0, 20.0, 320, "Miller2"),
    325: RFProfile(325, "PR_ASK", 2.0, 15.0, 320, "Miller2"),
    326: RFProfile(326, "PR_ASK", 1.5, 12.5, 320, "Miller2"),
    342: RFProfile(342, "PR_ASK", 2.0, 20.0, 320, "Miller4"),
    343: RFProfile(343, "PR_ASK", 2.0, 20.0, 250, "Miller4"),
    344: RFProfile(344, "PR_ASK", 2.0, 7.5, 640, "Miller4"),
    345: RFProfile(345, "PR_ASK", 1.5, 7.5, 640, "Miller4"),
    382: RFProfile(382, "PR_ASK", 2.0, 20.0, 160, "Miller8"),
    4123: RFProfile(4123, "PR_ASK", 2.0, 20.0, 320, "PSK2"),
    4124: RFProfile(4124, "PR_ASK", 2.0, 7.5, 640, "BPSK2"),
    4141: RFProfile(4141, "PR_ASK", 2.0, 20.0, 320, "BPSK4"),
    4146: RFProfile(4146, "PR_ASK", 2.0, 20.0, 250, "BPSK4"),
    4148: RFProfile(4148, "PR_ASK", 1.5, 7.5, 640, "BPSK4"),
    4185: RFProfile(4185, "PR_ASK", 2.0, 20.0, 160, "BPSK8"),
    5123: RFProfile(5123, "PR_ASK", 2.0, 20.0, 320, "M+B2"),
    5124: RFProfile(5124, "PR_ASK", 2.0, 7.5, 640, "M+B2"),
    5141: RFProfile(5141, "PR_ASK", 2.0, 20.0, 320, "M+B4"),
    5146: RFProfile(5146, "PR_ASK", 2.0, 20.0, 250, "M+B4"),
    5148: RFProfile(5148, "PR_ASK", 1.5, 7.5, 640, "M+B4"),
    5185: RFProfile(5185, "PR_ASK", 2.0, 20.0, 160, "M+B8"),
}


def get_profile_definition(profile_id: int) -> RFProfile:
    try:
        return PROFILES[profile_id]
    except KeyError as error:
        raise UnverifiedFeature(
            f"No physical definition for native profile {profile_id}"
        ) from error
