"""Baseline integrity check without importing threading/serial upstream into core."""

import hashlib
from pathlib import Path


def test_reference_matches_documented_english_revision():
    root = Path(__file__).parents[3] / "compat/nation"
    assert (
        hashlib.sha256((root / "nrn.py").read_bytes()).hexdigest()
        == "b1d6c13db195428c73ee1df390a18b93ff6f0ad1d5b4864a36c006751211747a"
    )
    assert (
        hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest()
        == "faaf4cdb3a3c000b6084cb82ab938c465756d2925d5c11b76d78aa56388c2741"
    )
