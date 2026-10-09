"""Baseline integrity check without importing threading/serial upstream into core."""

import hashlib
from pathlib import Path


def test_reference_is_byte_identical_to_pinned_upstream():
    root = Path(__file__).parents[3] / "compat/nation"
    assert (
        hashlib.sha256((root / "nrn.py").read_bytes()).hexdigest()
        == "28ffcbd698a04dc35a324c7b7b3cfdb8edc2ff7b61dd730924e29c6cc1975596"
    )
    assert (
        hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest()
        == "faaf4cdb3a3c000b6084cb82ab938c465756d2925d5c11b76d78aa56388c2741"
    )
