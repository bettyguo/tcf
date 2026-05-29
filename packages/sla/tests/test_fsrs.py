"""FSRS-6 wrapper invariants.

These tests do not check bit-identity to the reference `fsrs` package
(that conformance test is deferred — see ADR-023 and
`phase4_audit.md §1`). They check the FSRS-shape invariants any
correct implementation must satisfy:

- First-review stability is rating-monotone (Easy > Good > Hard > Again).
- AGAIN never increases stability past the pre-review value.
- Retrievability `R(t, S)` is monotone decreasing in `t` and tends to 1
  as `t → 0` and to 0 as `t → ∞`.
- The next-review due-date is always strictly in the future for any
  rating except a degenerate-tiny stability.
- The card's `n_reviews` counter increments by exactly one per call.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tcf_accel_sla.scheduler.fsrs import (
    Card,
    FSRSScheduler,
    Rating,
    retrievability,
)


def _now() -> datetime:
    return datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def test_first_review_stability_is_rating_monotone() -> None:
    s = FSRSScheduler()
    stabilities = {}
    now = _now()
    for rating in Rating:
        card, _ = s.review(Card.new(), rating, now)
        stabilities[rating] = card.stability
    assert stabilities[Rating.EASY] > stabilities[Rating.GOOD]
    assert stabilities[Rating.GOOD] > stabilities[Rating.HARD]
    assert stabilities[Rating.HARD] > stabilities[Rating.AGAIN]


def test_again_never_grows_stability_past_prior() -> None:
    s = FSRSScheduler()
    now = _now()
    card = Card.new()
    card, _ = s.review(card, Rating.GOOD, now)
    later = now + timedelta(days=2)
    card_after_fail, _ = s.review(card, Rating.AGAIN, later)
    assert card_after_fail.stability <= card.stability


def test_retrievability_monotone_in_time() -> None:
    s = 10.0
    rs = [retrievability(s, t) for t in (0.1, 1.0, 5.0, 20.0, 100.0)]
    assert rs == sorted(rs, reverse=True)
    assert retrievability(s, 0.0) == 1.0
    assert retrievability(s, 1e9) < 1e-2


def test_due_date_strictly_in_future() -> None:
    s = FSRSScheduler()
    now = _now()
    for rating in Rating:
        card, _ = s.review(Card.new(), rating, now)
        assert card.due > now


def test_n_reviews_increments_by_one() -> None:
    s = FSRSScheduler()
    now = _now()
    card = Card.new()
    assert card.n_reviews == 0
    for i in range(5):
        card, _ = s.review(card, Rating.GOOD, now + timedelta(days=i))
        assert card.n_reviews == i + 1


def test_invalid_weights_length_rejected() -> None:
    with pytest.raises(ValueError, match="weights must have length 21"):
        FSRSScheduler(weights=(0.1,) * 20)


def test_invalid_retention_rejected() -> None:
    with pytest.raises(ValueError, match="desired_retention"):
        FSRSScheduler(desired_retention=0.1)


def test_clock_skew_rejected() -> None:
    s = FSRSScheduler()
    now = _now()
    card, _ = s.review(Card.new(), Rating.GOOD, now)
    with pytest.raises(ValueError, match="before card's last review"):
        s.review(card, Rating.GOOD, now - timedelta(days=1))


def test_optimize_returns_defaults_on_v1() -> None:
    """ADR-023: per-user optimization is a no-op in Phase 4."""
    s = FSRSScheduler()
    out = s.optimize(history=[])
    assert out == s.weights
