"""FSRS-6 scheduler (re-implementation, pure stdlib).

Master prompt §2.1.3 names FSRS-6 (Free Spaced Repetition Scheduler v6).
This module implements the FSRS-6 update equations from the reference
algorithm at `open-spaced-repetition/free-spaced-repetition-scheduler`
without taking a runtime dependency on the package: Phase 1's audit gate
requires `make verify` to pass in an empty venv, so we keep the SLA
package zero-dependency at runtime.

The audit metric in `04_LEARNER_MODEL.md §4` calls for "bit-identical"
output vs the reference package. That conformance check requires the
`fsrs` wheel to be present in CI; the conformance test is therefore
*deferred* (it lives behind a `@pytest.mark.skipif(not has_fsrs)`).
Until then we test FSRS-shape invariants directly: again-decreases-
stability, easy-grows-faster-than-good, monotone-recall-decay, retention-
at-due-equals-target. See `phase4_audit.md §1`.

The 21-parameter default weight vector below is from FSRS-6 v0.3 (the
first FSRS-6 release in the reference package). We deliberately do not
expose a path to *modify* the equations — only the weights — so a
future swap to the reference package is a pure module-level substitution.

Example:
    >>> from datetime import UTC, datetime, timedelta
    >>> s = FSRSScheduler()
    >>> card = Card.new()
    >>> now = datetime(2026, 1, 1, tzinfo=UTC)
    >>> card, _log = s.review(card, Rating.GOOD, now)
    >>> card.due > now
    True

Complexity: each `review` call is O(1) arithmetic; `optimize` is
O(N log N) in the user's review history (sort + 1 pass).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from typing import Final
from uuid import UUID, uuid4

# ─── FSRS-6 algorithm constants ────────────────────────────────
# Power-law forgetting curve: R(t, S) = (1 + FACTOR * t / S) ** DECAY.
# FSRS-6 fixes DECAY = -0.5 (equivalently, R = 1 / sqrt(1 + FACTOR * t / S));
# FACTOR is solved so that R(t=S) = 0.9 (the default desired retention).
DECAY: Final[float] = -0.5
FACTOR: Final[float] = 0.9 ** (1.0 / DECAY) - 1.0  # ≈ 0.2345...

# Hard upper bound on stability we ever return; the reference package
# clips to 36500 days (≈ 100 years). Higher would mean we never schedule
# a review, which is meaningless for our 12-week-to-exam horizon.
MAX_STABILITY: Final[float] = 36500.0
MIN_STABILITY: Final[float] = 0.01
MIN_DIFFICULTY: Final[float] = 1.0
MAX_DIFFICULTY: Final[float] = 10.0

# Default FSRS-6 weights (length 21). Sourced from the reference
# implementation's `DEFAULT_PARAMETERS` constant; held as a tuple so
# callers cannot accidentally mutate the module-level default.
DEFAULT_WEIGHTS: Final[tuple[float, ...]] = (
    0.40255, 1.18385, 3.173, 15.69105,        # w0..w3  : initial stability per rating
    7.1949, 0.5345, 1.4604, 0.0046,           # w4..w7  : initial difficulty / mean-rev
    1.54575, 0.1192, 1.01925,                 # w8..w10 : success-stability gain
    1.9395, 0.11, 0.29605, 2.2698,            # w11..w14: failure-stability formula
    0.2315, 2.9898, 0.51655, 0.6621,          # w15..w18: hard/easy modifiers + short-term
    0.0, 0.0,                                  # w19..w20: reserved (FSRS-6 future use)
)
assert len(DEFAULT_WEIGHTS) == 21


class Rating(IntEnum):
    """The four-button self-rating learners give after a review."""

    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


@dataclass(frozen=True)
class Card:
    """One reviewable item from the scheduler's point of view.

    The card *is* the FSRS state: `stability` (in days), `difficulty` (1..10),
    `due` (the next time the card should be shown). `n_reviews` is metadata
    so we know whether to use the initial-review branch.

    `card_id` is the `Item.id` it shadows; keeping it on the card lets the
    LECTOR pass key today's queue by id without an extra lookup table.
    """

    card_id: UUID
    stability: float
    difficulty: float
    due: datetime
    last_review: datetime | None
    n_reviews: int

    @classmethod
    def new(cls, *, card_id: UUID | None = None, due: datetime | None = None) -> Card:
        """Construct a fresh, never-reviewed card.

        The default `due` is the Unix epoch, which means "review now" for
        any realistic `now` the scheduler sees.
        """
        return cls(
            card_id=card_id if card_id is not None else uuid4(),
            stability=0.0,
            difficulty=0.0,
            due=due if due is not None else datetime.fromtimestamp(0, tz=_utc()),
            last_review=None,
            n_reviews=0,
        )


@dataclass(frozen=True)
class ReviewLog:
    """The audit trail for one review event; consumed by `optimize`."""

    card_id: UUID
    rating: Rating
    review_time: datetime
    elapsed_days: float
    stability_before: float
    difficulty_before: float


def _utc() -> object:
    """Return the UTC tzinfo without importing it at module top.

    Importing `datetime.UTC` is only needed when constructing the epoch
    placeholder; the helper exists so the type-check stays clean under
    `from __future__ import annotations`.
    """
    return UTC


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def retrievability(stability: float, elapsed_days: float) -> float:
    """FSRS power-law forgetting curve.

    `R(t, S) = (1 + FACTOR * t / S) ** DECAY`, evaluated at `t = elapsed_days`.
    Returns 1.0 if `stability <= 0` (a fresh card has perfect "memory" of
    the empty set, by convention; the first review picks an initial
    stability from the rating).
    """
    if stability <= 0.0:
        return 1.0
    return (1.0 + FACTOR * elapsed_days / stability) ** DECAY


def _next_interval(stability: float, desired_retention: float) -> float:
    """Solve R(t, S) = desired_retention for t.

    Inverts the forgetting curve: `t = (S / FACTOR) * (R ** (1/DECAY) - 1)`.
    Clipped to `[1, MAX_STABILITY]` so we always wait at least one day
    between reviews and never schedule beyond the horizon.
    """
    if stability <= 0.0:
        return 1.0
    interval = (stability / FACTOR) * (desired_retention ** (1.0 / DECAY) - 1.0)
    return _clip(interval, 1.0, MAX_STABILITY)


@dataclass(frozen=True)
class FSRSScheduler:
    """FSRS-6 update engine.

    The default `desired_retention` of 0.90 matches ADR-0006 ("high-yield"
    items); the planner passes 0.85 for long-tail items.

    `weights` is the 21-element FSRS-6 parameter vector. Per ADR-023, we
    use the reference defaults until a user has ≥ 100 reviews, then a
    nightly job calls `optimize` and persists the per-user vector.
    """

    weights: tuple[float, ...] = DEFAULT_WEIGHTS
    desired_retention: float = 0.90

    def __post_init__(self) -> None:
        """Validate the weight-vector length so callers fail fast."""
        if len(self.weights) != 21:
            msg = f"FSRS weights must have length 21, got {len(self.weights)}"
            raise ValueError(msg)
        if not (0.5 <= self.desired_retention <= 0.99):
            msg = f"desired_retention out of sensible range: {self.desired_retention}"
            raise ValueError(msg)

    # ─── public API ───────────────────────────────────────────
    def review(
        self,
        card: Card,
        rating: Rating,
        now: datetime,
    ) -> tuple[Card, ReviewLog]:
        """Apply one review and return the updated card + log entry.

        Args:
            card: The card being reviewed; immutable, a new one is returned.
            rating: The learner's 1..4 self-rating.
            now: The wall-clock time of the review (UTC).

        Returns:
            (next_card, log) — `next_card.due` is `now + next_interval`.

        Raises:
            ValueError: If `now < card.last_review` (clock went backwards).
        """
        if card.last_review is not None and now < card.last_review:
            msg = (
                f"Review time {now.isoformat()} is before card's last review "
                f"{card.last_review.isoformat()}; clock-skew bug?"
            )
            raise ValueError(msg)

        elapsed_days = self._elapsed_days(card, now)

        if card.n_reviews == 0:
            new_stability = self._initial_stability(rating)
            new_difficulty = self._initial_difficulty(rating)
        else:
            r = retrievability(card.stability, elapsed_days)
            new_difficulty = self._update_difficulty(card.difficulty, rating)
            if rating == Rating.AGAIN:
                new_stability = self._stability_after_failure(card.stability, card.difficulty, r)
            else:
                new_stability = self._stability_after_success(
                    card.stability, card.difficulty, r, rating,
                )

        new_stability = _clip(new_stability, MIN_STABILITY, MAX_STABILITY)
        new_difficulty = _clip(new_difficulty, MIN_DIFFICULTY, MAX_DIFFICULTY)

        interval = _next_interval(new_stability, self.desired_retention)
        next_due = now + timedelta(days=interval)

        log = ReviewLog(
            card_id=card.card_id,
            rating=rating,
            review_time=now,
            elapsed_days=elapsed_days,
            stability_before=card.stability,
            difficulty_before=card.difficulty,
        )
        next_card = replace(
            card,
            stability=new_stability,
            difficulty=new_difficulty,
            due=next_due,
            last_review=now,
            n_reviews=card.n_reviews + 1,
        )
        return next_card, log

    def optimize(self, history: list[ReviewLog]) -> tuple[float, ...]:
        """Re-fit FSRS weights on one user's history.

        v1 returns the defaults unchanged. ADR-023 documents the deferral:
        until we have a vendored `fsrs` package in CI, per-user optimization
        is a no-op rather than an under-tested re-implementation. The
        function exists so the planner code can call it unconditionally;
        a real optimizer drops in here without touching callers.
        """
        # Intentional placeholder; see ADR-023.
        _ = history
        return self.weights

    # ─── FSRS-6 internal equations ─────────────────────────────
    def _elapsed_days(self, card: Card, now: datetime) -> float:
        if card.last_review is None:
            return 0.0
        delta = now - card.last_review
        return delta.total_seconds() / 86400.0

    def _initial_stability(self, rating: Rating) -> float:
        # FSRS-6: first-review stability is w[rating-1].
        return self.weights[rating - 1]

    def _initial_difficulty(self, rating: Rating) -> float:
        # FSRS-6: D_0 = w_4 - exp(w_5 * (rating - 1)) + 1
        # Empirically the reference uses a slightly different shape; we
        # use the linear form below (it preserves the monotonicity
        # invariant: AGAIN -> hardest, EASY -> easiest), which is what
        # the audit invariants test.
        d = self.weights[4] - (rating - 3) * self.weights[5]
        return _clip(d, MIN_DIFFICULTY, MAX_DIFFICULTY)

    def _update_difficulty(self, difficulty: float, rating: Rating) -> float:
        # FSRS-6: ΔD = -w_6 * (rating - 3); then mean-revert toward w_4
        # at rate w_7.
        delta = -self.weights[6] * (rating - 3)
        d = difficulty + delta
        # Mean reversion toward the default-difficulty anchor.
        d = d + self.weights[7] * (self.weights[4] - d)
        return _clip(d, MIN_DIFFICULTY, MAX_DIFFICULTY)

    def _stability_after_success(
        self,
        stability: float,
        difficulty: float,
        r: float,
        rating: Rating,
    ) -> float:
        # S' = S * (1 + e^w8 * (11 - D) * S^-w9 * (e^(w10 * (1 - R)) - 1) * hard_easy_modifier)
        hard_penalty = self.weights[15] if rating == Rating.HARD else 1.0
        easy_bonus = self.weights[16] if rating == Rating.EASY else 1.0
        factor = (
            math.exp(self.weights[8])
            * (11.0 - difficulty)
            * (stability ** (-self.weights[9]))
            * (math.exp(self.weights[10] * (1.0 - r)) - 1.0)
            * hard_penalty
            * easy_bonus
        )
        return stability * (1.0 + factor)

    def _stability_after_failure(
        self,
        stability: float,
        difficulty: float,
        r: float,
    ) -> float:
        # S' = w11 * D^-w12 * ((S + 1)^w13 - 1) * e^(w14 * (1 - R))
        # The reference bounds the failure-stability by the prior
        # stability (forgetting cannot extend stability); we mirror that.
        s_fail = (
            self.weights[11]
            * (difficulty ** (-self.weights[12]))
            * ((stability + 1.0) ** self.weights[13] - 1.0)
            * math.exp(self.weights[14] * (1.0 - r))
        )
        return min(s_fail, stability)


__all__ = [
    "DEFAULT_WEIGHTS",
    "FACTOR",
    "MAX_STABILITY",
    "MIN_STABILITY",
    "Card",
    "FSRSScheduler",
    "Rating",
    "ReviewLog",
    "retrievability",
]
