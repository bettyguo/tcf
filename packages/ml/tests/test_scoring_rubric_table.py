"""Rubric-table monotone mapping (ADR-036, Phase 7)."""

from __future__ import annotations

from tcf_accel_ml.scoring.rubric_table import nclc_from_total_20


def test_mapping_is_monotone() -> None:
    prev = -1
    for total in range(0, 21):
        nclc = nclc_from_total_20(total)
        assert nclc >= prev
        prev = nclc


def test_mapping_in_bounds() -> None:
    for total in range(0, 21):
        assert 3 <= nclc_from_total_20(total) <= 12


def test_mapping_specific_thresholds() -> None:
    assert nclc_from_total_20(0) == 3
    assert nclc_from_total_20(15) == 9   # target band
    assert nclc_from_total_20(20) == 12


def test_mapping_clamps_out_of_range() -> None:
    assert nclc_from_total_20(-5) == 3
    assert nclc_from_total_20(99) == 12
