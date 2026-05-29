"""Scheduling primitives: FSRS-6 + LECTOR semantic spacer.

See `04_LEARNER_MODEL.md §2.1` (FSRS) and `§2.2` (LECTOR) for the
contracts these modules implement; see ADR-023 + ADR-024 for the
trade-offs that justify the split.
"""

from __future__ import annotations

from tcf_accel_sla.scheduler.fsrs import (
    DEFAULT_WEIGHTS,
    Card,
    FSRSScheduler,
    Rating,
    ReviewLog,
)
from tcf_accel_sla.scheduler.lector import (
    MAX_LECTOR_DELAY_DAYS,
    SIMILARITY_THRESHOLD,
    adjust_due_with_lector,
    cosine_similarity,
    lector_spacing_penalty,
)

__all__ = [
    "DEFAULT_WEIGHTS",
    "MAX_LECTOR_DELAY_DAYS",
    "SIMILARITY_THRESHOLD",
    "Card",
    "FSRSScheduler",
    "Rating",
    "ReviewLog",
    "adjust_due_with_lector",
    "cosine_similarity",
    "lector_spacing_penalty",
]
