"""Exam-shape constants — FEI structure, durations, breaks.

Source of truth: `06_MOCK_EXAM_ENGINE.md` §2.1 and TCF Canada
candidate handbook. The constants are *frozen*; any change requires
ADR-032's amendment and a SCHEMA_VERSION bump.

Per-module durations sum to **2h47** (167 min) of active test time
(`ACTIVE_DURATION_S`). Adding the published 5/5/15 inter-module breaks
brings the total wall-clock to **3h12** (`TOTAL_DURATION_S`). The
"2h47" figure quoted in the spec is the active-test figure.

The `FEI_SPREAD` is the difficulty distribution the selector targets:
the per-mock item population must touch every CEFR band so the score
generalizes (a learner at NCLC 8 still needs to see a few C1/C2 items
to ceil-out, even if most items are at B2).
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.item import CefrLevel, Module

EXAM_SHAPE: Final[dict[Module, int]] = {
    "CO": 39,
    "CE": 39,
    "EE": 3,
    "EO": 3,
}

MODULE_ORDER: Final[tuple[Module, ...]] = ("CO", "CE", "EE", "EO")

MODULE_DURATION_S: Final[dict[Module, int]] = {
    "CO": 35 * 60,   # 2100 s
    "CE": 60 * 60,   # 3600 s
    "EE": 60 * 60,   # 3600 s
    "EO": 12 * 60,   #  720 s
}

# Published TCF Canada inter-module breaks.
BREAK_DURATION_S: Final[dict[str, int]] = {
    "BREAK_1": 5 * 60,   # after CO
    "BREAK_2": 5 * 60,   # after CE
    "BREAK_3": 15 * 60,  # after EE
}

ACTIVE_DURATION_S: Final[int] = sum(MODULE_DURATION_S.values())   # 10020 s = 2h47
TOTAL_DURATION_S: Final[int] = ACTIVE_DURATION_S + sum(BREAK_DURATION_S.values())  # 11520 s = 3h12

FEI_SPREAD: Final[dict[CefrLevel, float]] = {
    "A1": 0.10,
    "A2": 0.15,
    "B1": 0.20,
    "B2": 0.25,
    "C1": 0.20,
    "C2": 0.10,
}

CANONICAL_TAB_BLUR_GRACE_S: Final[int] = 5

# Topic-cluster cap per module: no single topic-cluster_id may exceed
# 8% of a module's items. Tighter than the bank-level cap (which is
# ~12% per ADR-0022) because a single mock is a much smaller draw.
TOPIC_CLUSTER_CAP_FRACTION: Final[float] = 0.08

# Never-seen items must be ≥ 20% of CO/CE picks per FEI's novelty
# principle (so even repeat mock-takers get exposure they have not
# rehearsed). `06_MOCK_EXAM_ENGINE.md` §1.2.
NEVER_SEEN_FRACTION: Final[float] = 0.20


__all__ = [
    "ACTIVE_DURATION_S",
    "BREAK_DURATION_S",
    "CANONICAL_TAB_BLUR_GRACE_S",
    "EXAM_SHAPE",
    "FEI_SPREAD",
    "MODULE_DURATION_S",
    "MODULE_ORDER",
    "NEVER_SEEN_FRACTION",
    "TOPIC_CLUSTER_CAP_FRACTION",
    "TOTAL_DURATION_S",
]
