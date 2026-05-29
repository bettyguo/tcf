"""LECTOR spacing tests.

Invariants:
- Penalty is zero below the similarity threshold.
- Penalty reaches `MAX_LECTOR_DELAY_DAYS` at similarity = 1.0.
- Re-running `adjust_due_with_lector` on its own output is idempotent.
- Confusable pairs end up at least `MAX_LECTOR_DELAY_DAYS` apart in the
  resulting due-date order *or* not consecutive in the queue.
- Items without embeddings are passed through unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from tcf_accel_sla.scheduler.lector import (
    MAX_LECTOR_DELAY_DAYS,
    SIMILARITY_THRESHOLD,
    DueItem,
    adjust_due_with_lector,
    cosine_similarity,
    lector_spacing_penalty,
)


def _uid(n: int) -> UUID:
    return UUID(int=n)


def _now() -> datetime:
    return datetime(2026, 6, 1, tzinfo=UTC)


def test_penalty_zero_below_threshold() -> None:
    assert lector_spacing_penalty(0.5) == 0.0
    assert lector_spacing_penalty(SIMILARITY_THRESHOLD - 0.001) == 0.0


def test_penalty_reaches_cap_at_full_similarity() -> None:
    assert lector_spacing_penalty(1.0) == MAX_LECTOR_DELAY_DAYS


def test_penalty_quadratic_shape() -> None:
    # Mid-threshold (0.875) should be 25% of cap (quadratic at 0.5).
    expected = 0.25 * MAX_LECTOR_DELAY_DAYS
    assert abs(lector_spacing_penalty(0.875) - expected) < 1e-9


def test_cosine_similarity_orthogonal_zero() -> None:
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_cosine_similarity_identity_one() -> None:
    v = [3.0, 4.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_items_without_embeddings_passthrough() -> None:
    items = [
        DueItem(item_id=_uid(1), due=_now(), embedding=None),
        DueItem(item_id=_uid(2), due=_now() + timedelta(hours=1), embedding=None),
    ]
    out = adjust_due_with_lector(items, recently_reviewed=[])
    assert len(out) == 2
    # Order preserved by (due, id).
    assert out[0].item_id == _uid(1)
    assert out[1].item_id == _uid(2)


def test_confusable_pair_gets_shifted() -> None:
    """Two near-identical items scheduled the same minute → second shifts."""
    same_emb = [1.0, 0.0]
    items = [
        DueItem(item_id=_uid(1), due=_now(), embedding=same_emb),
        DueItem(item_id=_uid(2), due=_now(), embedding=same_emb),
    ]
    out = adjust_due_with_lector(items, recently_reviewed=[])
    # The later-positioned item gets shifted by MAX_LECTOR_DELAY_DAYS.
    shifted = [i for i in out if i.due > _now()]
    assert len(shifted) == 1
    delay = (shifted[0].due - _now()).total_seconds() / 86400.0
    assert abs(delay - MAX_LECTOR_DELAY_DAYS) < 1e-6


def test_idempotent_under_repeated_application() -> None:
    same_emb = [1.0, 0.0]
    other_emb = [0.0, 1.0]
    items = [
        DueItem(item_id=_uid(1), due=_now(), embedding=same_emb),
        DueItem(item_id=_uid(2), due=_now(), embedding=same_emb),
        DueItem(item_id=_uid(3), due=_now(), embedding=other_emb),
    ]
    first = adjust_due_with_lector(items, recently_reviewed=[])
    second = adjust_due_with_lector(first, recently_reviewed=[])
    assert [(i.item_id, i.due) for i in first] == [(i.item_id, i.due) for i in second]


def test_unrelated_pair_not_shifted() -> None:
    """Items with cos sim < threshold do not move."""
    items = [
        DueItem(item_id=_uid(1), due=_now(), embedding=[1.0, 0.0]),
        DueItem(item_id=_uid(2), due=_now(), embedding=[0.0, 1.0]),  # orthogonal
    ]
    out = adjust_due_with_lector(items, recently_reviewed=[])
    for item in out:
        assert item.due == _now()
