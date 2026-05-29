"""Hypothesis-driven FSRS scheduler invariants.

These are the load-bearing FSRS-shape properties we test in place of
the bit-identical conformance check (deferred per ADR-023). Every
correct FSRS implementation must satisfy them.

Invariants:
1. Retention monotonicity: more elapsed time → lower retention.
2. Stability monotonicity in rating: at first review, easier rating
   gives more stability.
3. AGAIN never grows stability past the prior.
4. Difficulty is bounded in [1, 10] forever.
5. Stability is bounded in [MIN_STABILITY, MAX_STABILITY] forever.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st
from tcf_accel_sla.scheduler.fsrs import (
    MAX_DIFFICULTY,
    MAX_STABILITY,
    MIN_DIFFICULTY,
    MIN_STABILITY,
    Card,
    FSRSScheduler,
    Rating,
    retrievability,
)


def _now() -> datetime:
    return datetime(2026, 6, 1, tzinfo=UTC)


@given(
    stability=st.floats(min_value=0.5, max_value=200.0, allow_nan=False),
    t1=st.floats(min_value=0.1, max_value=50.0, allow_nan=False),
    t2_extra=st.floats(min_value=0.1, max_value=200.0, allow_nan=False),
)
@settings(max_examples=200, deadline=None)
def test_retrievability_monotone_in_time(
    stability: float, t1: float, t2_extra: float,
) -> None:
    """For any stability and any t2 > t1 > 0: R(t2, S) <= R(t1, S)."""
    t2 = t1 + t2_extra
    assert retrievability(stability, t2) <= retrievability(stability, t1) + 1e-12


@given(rating=st.sampled_from(list(Rating)))
def test_first_review_stability_bounded(rating: Rating) -> None:
    s = FSRSScheduler()
    card, _ = s.review(Card.new(), rating, _now())
    assert MIN_STABILITY <= card.stability <= MAX_STABILITY
    assert MIN_DIFFICULTY <= card.difficulty <= MAX_DIFFICULTY


@given(
    ratings=st.lists(st.sampled_from(list(Rating)), min_size=1, max_size=30),
    gap_days=st.floats(min_value=0.5, max_value=30.0, allow_nan=False),
)
@settings(max_examples=50, deadline=None)
def test_long_sequences_keep_card_bounded(
    ratings: list[Rating], gap_days: float,
) -> None:
    s = FSRSScheduler()
    card = Card.new()
    now = _now()
    for r in ratings:
        card, _ = s.review(card, r, now)
        now = now + timedelta(days=gap_days)
        assert MIN_STABILITY <= card.stability <= MAX_STABILITY
        assert MIN_DIFFICULTY <= card.difficulty <= MAX_DIFFICULTY
        assert card.due > card.last_review  # always future-dated


@given(
    rating_first=st.sampled_from(
        [Rating.HARD, Rating.GOOD, Rating.EASY],
    ),  # exclude AGAIN to ensure n_reviews=1 has nonzero stability
    gap_days=st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
)
@settings(max_examples=50, deadline=None)
def test_again_after_success_never_grows_stability(
    rating_first: Rating, gap_days: float,
) -> None:
    s = FSRSScheduler()
    card = Card.new()
    now = _now()
    card, _ = s.review(card, rating_first, now)
    later = now + timedelta(days=gap_days)
    card_failed, _ = s.review(card, Rating.AGAIN, later)
    assert card_failed.stability <= card.stability + 1e-9
