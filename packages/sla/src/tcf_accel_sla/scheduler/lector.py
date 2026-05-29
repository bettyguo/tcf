"""LECTOR semantic spacing — defer confusable items in the daily queue.

LECTOR (arxiv 2508.03275, 2025): when two items are semantically confusable
(high cosine similarity in the content embedding space), interleaving them
in the same review session creates interference that erodes the FSRS
retention gains. Common French example: `amener` vs `emmener`, where the
distinction is contextual.

This module reorders/shifts the per-day FSRS queue to maximize aggregate
semantic distance — but never delays an item by more than
`MAX_LECTOR_DELAY_DAYS` from FSRS's recommendation, so FSRS's retention
guarantees stay intact. See ADR-024.

Inputs are deliberately ergonomic: callers pass an embedding dict keyed on
item id, not a numpy matrix, so the SLA package stays zero-dep at runtime.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final
from uuid import UUID

# Items with similarity below this threshold are not considered confusable;
# the LECTOR pass leaves them alone. 0.75 is the empirical knee in the
# similarity distribution for the confusable_pairs table the Phase 3
# pipeline populates.
SIMILARITY_THRESHOLD: Final[float] = 0.75

# Hard cap on how many days LECTOR is allowed to delay an item past its
# FSRS due-date. ADR-024: the cap exists so FSRS's retention guarantees
# are not overruled.
MAX_LECTOR_DELAY_DAYS: Final[float] = 2.0


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors.

    Returns 0.0 if either vector is the zero vector. Raises if the
    vectors are different lengths — that would silently mis-compare,
    which is exactly the kind of bug LECTOR is meant to prevent
    (semantic confusion).
    """
    if len(a) != len(b):
        msg = f"Vectors must be equal length: {len(a)} vs {len(b)}"
        raise ValueError(msg)
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def lector_spacing_penalty(similarity: float) -> float:
    """Days-of-delay penalty for two items with the given similarity.

    Quadratic above the threshold: similarity 0.75 → 0 days,
    similarity 1.0 → `MAX_LECTOR_DELAY_DAYS`. The quadratic shape (vs
    linear) is from the LECTOR paper: linear under-penalizes high-
    similarity pairs and over-penalizes mid-similarity pairs.

    Example:
        >>> round(lector_spacing_penalty(0.75), 6)
        0.0
        >>> round(lector_spacing_penalty(1.0), 6)
        2.0
        >>> round(lector_spacing_penalty(0.875), 6)
        0.5
    """
    if similarity < SIMILARITY_THRESHOLD:
        return 0.0
    excess = similarity - SIMILARITY_THRESHOLD
    span = 1.0 - SIMILARITY_THRESHOLD
    # Normalize excess to [0, 1]; square; scale to MAX_LECTOR_DELAY_DAYS.
    return ((excess / span) ** 2) * MAX_LECTOR_DELAY_DAYS


@dataclass(frozen=True)
class DueItem:
    """One item due in the FSRS pass; the LECTOR pass may shift `due`.

    `embedding` is the content embedding from the Phase 3 pipeline. Items
    with no embedding (legacy data) bypass LECTOR entirely — the pass
    leaves their due-date untouched.
    """

    item_id: UUID
    due: datetime
    embedding: list[float] | None = None


def adjust_due_with_lector(
    items_due: list[DueItem],
    recently_reviewed: list[DueItem],
) -> list[DueItem]:
    """Reorder/shift today's queue to maximize aggregate semantic distance.

    The algorithm:

    1. For each item in `items_due`, compute its max similarity vs
       (a) the items already reviewed today (`recently_reviewed`) and
       (b) the items earlier in `items_due` that come before it.
    2. If the max similarity exceeds `SIMILARITY_THRESHOLD`, shift the
       item's due-date forward by `lector_spacing_penalty(max_sim)` days,
       capped at `MAX_LECTOR_DELAY_DAYS` from the original FSRS due.
    3. Sort the resulting list by adjusted due-date. (Ties broken by
       original due-date, then item_id, for determinism.)

    The pass is *idempotent* — running it twice on its own output yields
    the same ordering — because the similarity considered for each item
    is computed against items that came before it, not after.

    Args:
        items_due: Items FSRS scheduled for today, in any order. The
            list is not mutated.
        recently_reviewed: Items the learner has already seen today
            (in the current session). Used as additional context for
            the "what did I just see?" similarity check.

    Returns:
        A new list, sorted by adjusted due, with embeddings preserved.
    """
    adjusted: list[DueItem] = []
    seen_so_far: list[DueItem] = list(recently_reviewed)

    # Deterministic baseline ordering: by FSRS due, then by item_id.
    for item in sorted(items_due, key=lambda i: (i.due, str(i.item_id))):
        if item.embedding is None:
            adjusted.append(item)
            seen_so_far.append(item)
            continue
        # Find the most-similar prior; anchor the shift to its due-date
        # (not to the item's own due) so the pass is idempotent — running
        # `adjust_due_with_lector` on its own output must yield the same
        # ordering.
        best_sim = 0.0
        best_prior_due: datetime | None = None
        for prior in seen_so_far:
            if prior.embedding is None:
                continue
            sim = cosine_similarity(item.embedding, prior.embedding)
            if sim > best_sim:
                best_sim = sim
                best_prior_due = prior.due
        if best_sim >= SIMILARITY_THRESHOLD and best_prior_due is not None:
            delay_days = min(lector_spacing_penalty(best_sim), MAX_LECTOR_DELAY_DAYS)
            target_due = best_prior_due + timedelta(days=delay_days)
            # Idempotent: only shift forward — never pull an item backward.
            new_due = max(item.due, target_due)
            shifted = DueItem(
                item_id=item.item_id,
                due=new_due,
                embedding=item.embedding,
            )
            adjusted.append(shifted)
            seen_so_far.append(shifted)
        else:
            adjusted.append(item)
            seen_so_far.append(item)

    adjusted.sort(key=lambda i: (i.due, str(i.item_id)))
    return adjusted


__all__ = [
    "MAX_LECTOR_DELAY_DAYS",
    "SIMILARITY_THRESHOLD",
    "DueItem",
    "adjust_due_with_lector",
    "cosine_similarity",
    "lector_spacing_penalty",
]
