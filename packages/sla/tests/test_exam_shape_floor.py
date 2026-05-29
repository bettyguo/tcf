"""Unit tests for the exam-shape floor (ADR-028)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tcf_accel_sla.session import (
    EXAM_SHAPE_FLOOR_MIN,
    SessionRecord,
    floor_satisfied,
    is_exam_shape_drill,
    iso_week,
    rolling_7d_exam_shape_minutes,
)

_NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


def _rec(*, days_ago: float, exam_shape: bool, minutes: int) -> SessionRecord:
    return SessionRecord(
        finished_at=_NOW - timedelta(days=days_ago),
        exam_shape=exam_shape,
        target_minutes=minutes,
    )


def test_is_exam_shape_drill() -> None:
    assert is_exam_shape_drill("mock_section") is True
    assert is_exam_shape_drill("writing_long") is True
    assert is_exam_shape_drill("speaking_mono") is True
    assert is_exam_shape_drill("mcq") is False
    assert is_exam_shape_drill("co_dictation") is False


def test_iso_week_format() -> None:
    assert iso_week(_NOW) == "2026-W22"


def test_rolling_window_excludes_old_and_nonexam() -> None:
    records = [
        _rec(days_ago=1, exam_shape=True, minutes=30),  # counts
        _rec(days_ago=2, exam_shape=False, minutes=60),  # not exam-shape
        _rec(days_ago=8, exam_shape=True, minutes=40),  # outside window
    ]
    assert rolling_7d_exam_shape_minutes(records, now=_NOW) == 30


def test_unfinished_session_does_not_count() -> None:
    records = [SessionRecord(finished_at=None, exam_shape=True, target_minutes=60)]
    assert rolling_7d_exam_shape_minutes(records, now=_NOW) == 0


def test_floor_blocks_zero_exam_shape() -> None:
    records = [_rec(days_ago=1, exam_shape=False, minutes=60)]
    assert floor_satisfied(records, now=_NOW, dismissed_this_week=False) is False


def test_floor_satisfied_when_minutes_meet_threshold() -> None:
    records = [_rec(days_ago=1, exam_shape=True, minutes=EXAM_SHAPE_FLOOR_MIN)]
    assert floor_satisfied(records, now=_NOW, dismissed_this_week=False) is True


def test_dismissal_satisfies_floor() -> None:
    records = [_rec(days_ago=1, exam_shape=False, minutes=60)]
    assert floor_satisfied(records, now=_NOW, dismissed_this_week=True) is True


def test_floor_cannot_be_configured_below_lower_bound() -> None:
    # 25 exam-shape minutes with a misconfigured floor_min=10 must still
    # fail, because the effective floor is clamped to EXAM_SHAPE_FLOOR_LOWER=20.
    records = [_rec(days_ago=1, exam_shape=True, minutes=25)]
    # 25 >= 20 → satisfied; but 19 would not be.
    assert floor_satisfied(records, now=_NOW, dismissed_this_week=False, floor_min=10) is True
    records_low = [_rec(days_ago=1, exam_shape=True, minutes=19)]
    assert floor_satisfied(records_low, now=_NOW, dismissed_this_week=False, floor_min=10) is False
