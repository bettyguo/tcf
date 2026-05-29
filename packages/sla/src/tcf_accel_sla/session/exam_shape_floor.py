"""Exam-shape floor (ADR-028, `phase5_design.md §8`).

The 80/20 drill/exam-shape doctrine (`05_PRACTICE_AND_DRILLS.md §1.3`)
is enforced as a **hard floor + soft cadence**: the planner nudges the
80/20 split, but `POST /v1/session/start` *refuses* a non-exam-shape
drill if the learner has logged zero exam-shape time in the rolling
7-day window and has not dismissed the floor for the current ISO week.

This module is the pure computation: given a learner's recent session
records and the current time, is the floor satisfied? The stateful
store + the 409 wiring live in the API layer.

The catastrophic failure mode is the *zero* week (a learner who only
ever drills with feedback and never practices exam-shape), not a 75/25
vs 80/20 drift — so the floor targets the zero boundary, and a
dismissal (logged, audited) lets the learner override it once per week.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from tcf_accel.schemas.api.plan import DrillType

# A session counts as "exam-shape" if its drill type is one of these:
# full mock sections (Phase 6) or the timed production tasks that mirror
# the exam's own withhold-feedback-until-the-end shape. These are the
# `DrillType` values (what `SessionStart.drill_type` carries) that map
# to the exam-shape `DrillKind`s {mock_section, ee_task, eo_task} —
# i.e. the 3-task timed write/speak and the full mock section.
EXAM_SHAPE_DRILL_TYPES: Final[frozenset[DrillType]] = frozenset(
    {"mock_section", "writing_short", "writing_long", "speaking_mono", "speaking_role"},  # type: ignore[arg-type]
)

# Rolling-7-day minimum exam-shape minutes. The operator may raise this
# but not below EXAM_SHAPE_FLOOR_LOWER — twenty minutes is roughly one
# CE half-section under exam pace, the smallest unit that resembles
# exam shape.
EXAM_SHAPE_FLOOR_MIN: Final[int] = 30
EXAM_SHAPE_FLOOR_LOWER: Final[int] = 20

_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class SessionRecord:
    """Minimal projection of a finished session for the floor computation."""

    finished_at: datetime | None
    exam_shape: bool
    target_minutes: int


def is_exam_shape_drill(drill_type: DrillType) -> bool:
    """True iff a session of this drill type counts toward the floor.

    Example:
        >>> is_exam_shape_drill("mock_section")
        True
        >>> is_exam_shape_drill("mcq")
        False
    """
    return drill_type in EXAM_SHAPE_DRILL_TYPES


def iso_week(when: datetime) -> str:
    """ISO-week designator, e.g. '2026-W22'.

    Used to key dismissals: one dismissal clears the floor for the
    named calendar week.

    Example:
        >>> from datetime import UTC, datetime
        >>> iso_week(datetime(2026, 5, 28, tzinfo=UTC))
        '2026-W22'
    """
    year, week, _ = when.isocalendar()
    return f"{year}-W{week:02d}"


def rolling_7d_exam_shape_minutes(
    records: list[SessionRecord],
    *,
    now: datetime,
) -> int:
    """Sum exam-shape minutes from sessions finished in the last 7 days.

    Only *finished* exam-shape sessions count; an in-flight session
    doesn't yet satisfy the floor.

    Complexity: O(len(records)).
    """
    cutoff = now - _WINDOW
    return sum(
        r.target_minutes
        for r in records
        if r.exam_shape and r.finished_at is not None and r.finished_at > cutoff
    )


def floor_satisfied(
    records: list[SessionRecord],
    *,
    now: datetime,
    dismissed_this_week: bool,
    floor_min: int = EXAM_SHAPE_FLOOR_MIN,
) -> bool:
    """Is the exam-shape floor satisfied for starting a non-exam-shape drill?

    Satisfied iff the rolling-7-day exam-shape minutes meet the floor,
    OR the learner dismissed the floor for the current ISO week.

    The `floor_min` is clamped to `EXAM_SHAPE_FLOOR_LOWER` so an operator
    misconfiguration cannot disable the doctrine entirely.

    Complexity: O(len(records)).
    """
    effective_floor = max(floor_min, EXAM_SHAPE_FLOOR_LOWER)
    if rolling_7d_exam_shape_minutes(records, now=now) >= effective_floor:
        return True
    return dismissed_this_week


__all__ = [
    "EXAM_SHAPE_DRILL_TYPES",
    "EXAM_SHAPE_FLOOR_LOWER",
    "EXAM_SHAPE_FLOOR_MIN",
    "SessionRecord",
    "floor_satisfied",
    "is_exam_shape_drill",
    "iso_week",
    "rolling_7d_exam_shape_minutes",
]
