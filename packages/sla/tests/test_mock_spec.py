"""Mock-exam shape constants — FEI conformance.

`phase6_audit.md §1` invariants: 39/39/3/3 item count; 167-minute
active duration; 25-minute total breaks; total wall-clock 3h12.
"""

from __future__ import annotations

from tcf_accel_sla.mock_exam.spec import (
    ACTIVE_DURATION_S,
    BREAK_DURATION_S,
    CANONICAL_TAB_BLUR_GRACE_S,
    EXAM_SHAPE,
    FEI_SPREAD,
    MODULE_DURATION_S,
    MODULE_ORDER,
    TOTAL_DURATION_S,
)


def test_exam_shape_counts_match_fei() -> None:
    assert EXAM_SHAPE == {"CO": 39, "CE": 39, "EE": 3, "EO": 3}


def test_module_order_is_canonical() -> None:
    assert MODULE_ORDER == ("CO", "CE", "EE", "EO")


def test_module_durations_sum_to_2h47() -> None:
    assert ACTIVE_DURATION_S == 35 * 60 + 60 * 60 + 60 * 60 + 12 * 60
    assert ACTIVE_DURATION_S == 167 * 60


def test_breaks_sum_to_25_minutes() -> None:
    assert sum(BREAK_DURATION_S.values()) == 25 * 60


def test_total_duration_consistent() -> None:
    assert TOTAL_DURATION_S == ACTIVE_DURATION_S + sum(BREAK_DURATION_S.values())


def test_fei_spread_sums_to_one() -> None:
    total = sum(FEI_SPREAD.values())
    assert abs(total - 1.0) < 1e-9


def test_grace_window_is_five_seconds() -> None:
    assert CANONICAL_TAB_BLUR_GRACE_S == 5


def test_module_duration_keys_match_shape() -> None:
    assert set(MODULE_DURATION_S.keys()) == set(EXAM_SHAPE.keys())
