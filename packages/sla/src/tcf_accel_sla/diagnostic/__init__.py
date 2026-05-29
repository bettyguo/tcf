"""Computer-adaptive diagnostic (CAT).

See `04_LEARNER_MODEL.md §1.3` and ADR-026 for the contract.
"""

from __future__ import annotations

from tcf_accel_sla.diagnostic.cat import (
    DIAGNOSTIC_MAX_ITEMS,
    DIAGNOSTIC_STOP_VARIANCE,
    SAME_DIFFICULTY_RUN_CAP,
    CandidateItem,
    DiagnosticSession,
    select_next_item,
)

__all__ = [
    "DIAGNOSTIC_MAX_ITEMS",
    "DIAGNOSTIC_STOP_VARIANCE",
    "SAME_DIFFICULTY_RUN_CAP",
    "CandidateItem",
    "DiagnosticSession",
    "select_next_item",
]
