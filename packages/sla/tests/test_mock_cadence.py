"""Mock-cadence cap (ADR-033) — 1/w → 2/w → 3/w."""

from __future__ import annotations

from datetime import UTC, datetime

from tcf_accel_sla.mock_exam import (
    MOCK_CADENCE_TABLE,
    can_start_canonical,
    can_start_training,
    mocks_allowed_per_iso_week,
    week_index_since,
)
from tcf_accel_sla.mock_exam.cadence import MockExamSummary


def test_cadence_table_covers_full_ladder() -> None:
    assert MOCK_CADENCE_TABLE[0] == (0, 5, 1)
    assert MOCK_CADENCE_TABLE[1] == (6, 9, 2)
    assert MOCK_CADENCE_TABLE[2] == (10, 999, 3)


def test_mocks_allowed_per_week() -> None:
    assert mocks_allowed_per_iso_week(0) == 1
    assert mocks_allowed_per_iso_week(5) == 1
    assert mocks_allowed_per_iso_week(6) == 2
    assert mocks_allowed_per_iso_week(9) == 2
    assert mocks_allowed_per_iso_week(10) == 3
    assert mocks_allowed_per_iso_week(50) == 3


def test_week_index_since_basic() -> None:
    first = datetime(2026, 4, 1, tzinfo=UTC)
    assert week_index_since(first, first) == 0
    assert week_index_since(first, datetime(2026, 4, 7, tzinfo=UTC)) == 0
    assert week_index_since(first, datetime(2026, 4, 8, tzinfo=UTC)) == 1
    assert week_index_since(first, datetime(2026, 6, 17, tzinfo=UTC)) >= 10


def test_week_index_none_first() -> None:
    assert week_index_since(None, datetime(2026, 5, 28, tzinfo=UTC)) == 0


def test_can_start_when_history_empty() -> None:
    allowed, _ = can_start_canonical(
        history=[],
        now=datetime(2026, 5, 28, tzinfo=UTC),
        first_mock_at=None,
    )
    assert allowed


def test_second_canonical_in_same_week_denied_early() -> None:
    first_at = datetime(2026, 5, 26, tzinfo=UTC)
    hist = [MockExamSummary(started_at=first_at, mode="canonical")]
    allowed, reason = can_start_canonical(
        history=hist,
        now=datetime(2026, 5, 28, tzinfo=UTC),  # same ISO week
        first_mock_at=first_at,
    )
    assert not allowed
    assert "weekly_cap" in reason


def test_third_canonical_allowed_in_late_phase() -> None:
    first_at = datetime(2026, 1, 1, tzinfo=UTC)  # many weeks ago
    same_week_dates = [
        datetime(2026, 5, 25, tzinfo=UTC),  # Mon
        datetime(2026, 5, 26, tzinfo=UTC),  # Tue
    ]
    hist = [MockExamSummary(started_at=d, mode="canonical") for d in same_week_dates]
    allowed, _ = can_start_canonical(
        history=hist,
        now=datetime(2026, 5, 28, tzinfo=UTC),  # same week, 3rd attempt
        first_mock_at=first_at,
    )
    # week index ~ 21 → cap 3 → 2 used → 3rd allowed.
    assert allowed


def test_forfeited_mocks_do_not_count_against_cadence() -> None:
    first_at = datetime(2026, 5, 26, tzinfo=UTC)
    hist = [
        MockExamSummary(started_at=first_at, mode="canonical", forfeited=True),
    ]
    allowed, _ = can_start_canonical(
        history=hist,
        now=datetime(2026, 5, 28, tzinfo=UTC),
        first_mock_at=first_at,
    )
    assert allowed  # forfeited doesn't burn the cap


def test_training_cap_one_per_day() -> None:
    today = datetime(2026, 5, 28, 10, tzinfo=UTC)
    hist = [MockExamSummary(started_at=today, mode="training")]
    allowed, _ = can_start_training(
        hist, now=datetime(2026, 5, 28, 18, tzinfo=UTC),
    )
    assert not allowed
    allowed, _ = can_start_training(
        hist, now=datetime(2026, 5, 29, 10, tzinfo=UTC),
    )
    assert allowed
