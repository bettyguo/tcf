"""Mock selector — shape conformance, determinism, and basic diversity."""

from __future__ import annotations

from collections import Counter
from uuid import uuid4

from tcf_accel.ids import UserId

from tcf_accel_sla.mock_exam import (
    EXAM_SHAPE,
    SelectorInputs,
    select_for_module,
    select_full_mock,
)
from tcf_accel_sla.mock_exam.selector import PooledMockItem
from tcf_accel_sla.mock_exam.spec import NEVER_SEEN_FRACTION


def _bank():
    # Defer to the API-side fixture to keep the SLA tests dependency-free
    # except for `tcf_accel_api.mock_exam_pool` which is part of the
    # workspace; the import is via the apps tree but the bank is pure data.
    from tcf_accel_api.mock_exam_pool import mock_bank

    return mock_bank()


def test_select_full_mock_returns_exact_counts() -> None:
    bank = _bank()
    inputs = SelectorInputs(
        user_id=UserId(uuid4()), iso_week="2026-W22", bank=bank,
    )
    result = select_full_mock(inputs)
    for module in ("CO", "CE", "EE", "EO"):
        assert len(result[module].items) == EXAM_SHAPE[module]


def test_selector_is_deterministic_per_user_and_week() -> None:
    bank = _bank()
    uid = UserId(uuid4())
    a = select_full_mock(
        SelectorInputs(user_id=uid, iso_week="2026-W22", bank=bank),
    )
    b = select_full_mock(
        SelectorInputs(user_id=uid, iso_week="2026-W22", bank=bank),
    )
    assert [p.item.id for p in a["CO"].items] == [p.item.id for p in b["CO"].items]
    assert [p.item.id for p in a["EE"].items] == [p.item.id for p in b["EE"].items]


def test_selector_varies_across_weeks() -> None:
    bank = _bank()
    uid = UserId(uuid4())
    a = select_for_module(
        SelectorInputs(user_id=uid, iso_week="2026-W22", bank=bank), "CO",
    )
    b = select_for_module(
        SelectorInputs(user_id=uid, iso_week="2026-W23", bank=bank), "CO",
    )
    assert {p.item.id for p in a.items} != {p.item.id for p in b.items}


def test_ee_picks_one_per_task_number() -> None:
    bank = _bank()
    inputs = SelectorInputs(
        user_id=UserId(uuid4()), iso_week="2026-W22", bank=bank,
    )
    result = select_for_module(inputs, "EE")
    tasks = sorted(p.task_number for p in result.items if p.task_number is not None)
    assert tasks == [1, 2, 3]


def test_eo_picks_one_per_task_number() -> None:
    bank = _bank()
    inputs = SelectorInputs(
        user_id=UserId(uuid4()), iso_week="2026-W22", bank=bank,
    )
    result = select_for_module(inputs, "EO")
    tasks = sorted(p.task_number for p in result.items if p.task_number is not None)
    assert tasks == [1, 2, 3]


def test_co_is_sorted_by_ascending_difficulty() -> None:
    bank = _bank()
    inputs = SelectorInputs(
        user_id=UserId(uuid4()), iso_week="2026-W22", bank=bank,
    )
    result = select_for_module(inputs, "CO")
    diffs = [p.difficulty for p in result.items]
    assert diffs == sorted(diffs), "FEI ordering: ascending difficulty"


def test_recent_items_are_excluded() -> None:
    bank = _bank()
    co = bank["CO"]
    seen = frozenset(p.item.id for p in co[:50])
    inputs = SelectorInputs(
        user_id=UserId(uuid4()),
        iso_week="2026-W22",
        bank=bank,
        seen_within_30d=seen,
    )
    result = select_for_module(inputs, "CO")
    chosen_ids = {p.item.id for p in result.items}
    assert chosen_ids.isdisjoint(seen)


def test_novelty_budget_respected_when_some_items_already_seen() -> None:
    bank = _bank()
    co = bank["CO"]
    # Mark half the CO bank as "seen ever" (but not in last 30 days).
    seen_ever = frozenset(p.item.id for p in co[: len(co) // 2])
    inputs = SelectorInputs(
        user_id=UserId(uuid4()),
        iso_week="2026-W22",
        bank=bank,
        seen_ever=seen_ever,
    )
    result = select_for_module(inputs, "CO")
    never_seen_count = sum(1 for p in result.items if p.item.id not in seen_ever)
    expected_min = int(NEVER_SEEN_FRACTION * EXAM_SHAPE["CO"])
    assert never_seen_count >= expected_min - 1  # off-by-one tolerance


def test_co_picks_span_multiple_cefr_bands() -> None:
    bank = _bank()
    inputs = SelectorInputs(
        user_id=UserId(uuid4()), iso_week="2026-W22", bank=bank,
    )
    result = select_for_module(inputs, "CO")
    cefrs = Counter(p.cefr for p in result.items)
    # FEI spread requires every band touched at least once for CO (39 items).
    assert len(cefrs) >= 5


def test_diversity_across_100_simulated_weeks_covers_majority_of_bank() -> None:
    """ADR-035 audit: union ≥ 60% bank coverage over 100 weeks."""
    bank = _bank()
    uid = UserId(uuid4())
    union: set = set()
    for i in range(100):
        result = select_for_module(
            SelectorInputs(user_id=uid, iso_week=f"2026-W{i:02d}", bank=bank),
            "CO",
        )
        union.update(p.item.id for p in result.items)
    coverage = len(union) / len(bank["CO"])
    assert coverage >= 0.60, f"selector concentrated; coverage = {coverage:.0%}"
