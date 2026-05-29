"""Mock-cadence cap (ADR-033).

Recap from `06_MOCK_EXAM_ENGINE.md` §1.3 and `phase6_think.md` §1.4:

- Weeks 0..5 (first 6): **1 canonical mock per ISO week.**
- Weeks 6..9 (next 4):  **2 canonical mocks per ISO week.**
- Weeks 10+:            **3 canonical mocks per ISO week.**

Training mocks have a much looser cap: **1/day** (so a learner can
sit several practice mocks back-to-back without it counting against
the canonical schedule).

The "week" index is *since the learner's first canonical mock*, not
calendar week. A learner whose first mock was 2026-04-01 gets the
canonical cap-ladder starting 2026-04-01, regardless of when they
joined the platform.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final, Literal

from tcf_accel_sla.session.exam_shape_floor import iso_week

# (low, high, cap) — week index range inclusive, cap on canonical mocks.
MOCK_CADENCE_TABLE: Final[tuple[tuple[int, int, int], ...]] = (
    (0, 5, 1),
    (6, 9, 2),
    (10, 999, 3),
)

TRAINING_PER_DAY_CAP: Final[int] = 1

# Cooldown override is logged at WARN level; no maximum count, but
# audit flags ≥ 3 overrides per week as a chronic pattern.
OVERRIDE_AUDIT_WARN_AFTER: Final[int] = 3


@dataclass(frozen=True)
class MockExamSummary:
    """Minimal projection of a finished mock for cadence reasoning."""

    started_at: datetime
    mode: Literal["canonical", "training"]
    forfeited: bool = False


def week_index_since(first: datetime | None, now: datetime) -> int:
    """Return the 0-based week index of `now` since `first`.

    Returns 0 if `first is None` (a learner with no prior mock is in
    week 0 by definition).

    Example:
        >>> from datetime import UTC, datetime
        >>> first = datetime(2026, 4, 1, tzinfo=UTC)
        >>> week_index_since(first, datetime(2026, 4, 1, tzinfo=UTC))
        0
        >>> week_index_since(first, datetime(2026, 4, 15, tzinfo=UTC))
        2
        >>> week_index_since(None, datetime(2026, 4, 1, tzinfo=UTC))
        0
    """
    if first is None:
        return 0
    delta = now - first
    return max(0, delta.days // 7)


def mocks_allowed_per_iso_week(week_index: int) -> int:
    """Return the canonical-mock cap for a given since-first week index."""
    for low, high, cap in MOCK_CADENCE_TABLE:
        if low <= week_index <= high:
            return cap
    return MOCK_CADENCE_TABLE[-1][2]


def _canonical_in_iso_week(history: Sequence[MockExamSummary], target_week: str) -> int:
    return sum(
        1
        for h in history
        if h.mode == "canonical"
        and not h.forfeited
        and iso_week(h.started_at) == target_week
    )


def can_start_canonical(
    history: Sequence[MockExamSummary],
    *,
    now: datetime,
    first_mock_at: datetime | None,
) -> tuple[bool, str]:
    """Is the learner allowed to start a canonical mock right now?

    Returns (allowed, reason). `reason` is a human-readable string used
    both by the error envelope and by audit logs.

    Args:
        history: All prior mocks for the user.
        now: Current UTC time.
        first_mock_at: Timestamp of the learner's first canonical mock,
            or `None` if they have not sat one yet.

    Example:
        >>> from datetime import UTC, datetime
        >>> hist = [MockExamSummary(
        ...     started_at=datetime(2026, 5, 25, tzinfo=UTC),
        ...     mode="canonical",
        ... )]
        >>> allowed, reason = can_start_canonical(
        ...     hist, now=datetime(2026, 5, 28, tzinfo=UTC),
        ...     first_mock_at=datetime(2026, 5, 25, tzinfo=UTC),
        ... )
        >>> allowed
        False
    """
    week_idx = week_index_since(first_mock_at, now)
    cap = mocks_allowed_per_iso_week(week_idx)
    used = _canonical_in_iso_week(history, iso_week(now))
    if used >= cap:
        next_week_starts = _next_iso_monday(now)
        return False, (
            f"weekly_cap: {used}/{cap} canonical mocks used in ISO week "
            f"{iso_week(now)} (week index {week_idx} since first). "
            f"Next eligible at {next_week_starts.isoformat()}."
        )
    return True, f"allowed: {used}/{cap} used this ISO week."


def can_start_training(
    history: Sequence[MockExamSummary],
    *,
    now: datetime,
) -> tuple[bool, str]:
    """Is the learner allowed to start a training mock right now?

    Training cap is `TRAINING_PER_DAY_CAP` per calendar day (UTC).
    """
    today = now.date()
    used = sum(
        1
        for h in history
        if h.mode == "training" and h.started_at.date() == today
    )
    if used >= TRAINING_PER_DAY_CAP:
        return False, (
            f"daily_cap: {used}/{TRAINING_PER_DAY_CAP} training mocks today."
        )
    return True, f"allowed: {used}/{TRAINING_PER_DAY_CAP} used today."


def _next_iso_monday(now: datetime) -> datetime:
    """Return midnight UTC of the next ISO Monday after `now`."""
    days_until_monday = (7 - now.isoweekday() + 1) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    candidate = now + timedelta(days=days_until_monday)
    return candidate.replace(hour=0, minute=0, second=0, microsecond=0)


__all__ = [
    "MOCK_CADENCE_TABLE",
    "MockExamSummary",
    "OVERRIDE_AUDIT_WARN_AFTER",
    "TRAINING_PER_DAY_CAP",
    "can_start_canonical",
    "can_start_training",
    "mocks_allowed_per_iso_week",
    "week_index_since",
]
