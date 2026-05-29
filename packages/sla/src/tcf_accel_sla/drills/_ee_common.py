"""EE drill word-count gate (`phase5_design.md §4.3`).

All EE drills enforce the same word-count posture: FEI specifies a
band per task (60w / 120w / 180w), and submissions outside the
80–110% band of the target accept a piecewise-linear penalty. The
penalty is informational metadata on the `Interaction` — Phase 7's
rubric scorer reads it; Phase 5 emits it.

The penalty curve is deliberately gentle (cap at -4 of 20): the
TCF Canada rubric does not zero out an under/over-length response,
and the system mirrors that. The cap is the structural property; the
slope is tunable per release.
"""

from __future__ import annotations

import math
from typing import Final

# Canonical per-task target word counts (FEI 60/120/180; `master prompt §1.1`).
WORD_COUNT_TARGETS: Final[dict[int, int]] = {1: 60, 2: 120, 3: 180}

# Acceptable band: a submission inside [80%, 110%] of target gets penalty 0.
WORD_COUNT_BAND_LOW: Final[float] = 0.80
WORD_COUNT_BAND_HIGH: Final[float] = 1.10

# Penalty cap (-4 of 20). The slope below is per-5%-step outside the band.
WORD_COUNT_PENALTY_CAP: Final[int] = -4


def count_words(text: str) -> int:
    """Whitespace-split word count.

    The FEI rubric counts words by whitespace separation; punctuation
    attached to a word is part of that word, hyphenated compounds count
    as one. We follow the rubric's convention here so the audit metric
    (word-band penalty) lines up.

    Example:
        >>> count_words("Bonjour, c'est moi.")
        3
        >>> count_words("")
        0
    """
    return len(text.split())


def word_count_penalty(actual: int, target: int) -> int:
    """Piecewise-linear penalty for an out-of-band word count.

    Returns 0 inside [80%, 110%] of `target`. Outside the band, one
    penalty point per 5% step away from the nearest band edge, capped at
    `WORD_COUNT_PENALTY_CAP` (a negative integer).

    Example:
        >>> word_count_penalty(60, 60)
        0
        >>> word_count_penalty(48, 60)  # 80%: at the boundary
        0
        >>> word_count_penalty(45, 60)  # 75%, 1 step out
        -1
        >>> word_count_penalty(30, 60)  # 50%, 6 steps out → cap
        -4
        >>> word_count_penalty(72, 60)  # 120%, 2 steps over
        -2

    Complexity: O(1).
    """
    if target <= 0:
        return 0
    # Work in percentage points: 100 * actual / target gives an exact
    # value at round percentages (e.g. 75.0, 80.0, 110.0) and avoids
    # the float-precision artifact where `0.80 - 0.75` is `0.05 + ε`
    # and `ceil(ε/0.05)` rounds an exact 5%-step up to 2.
    ratio_pct = 100.0 * actual / target
    low_pct = WORD_COUNT_BAND_LOW * 100.0
    high_pct = WORD_COUNT_BAND_HIGH * 100.0
    if low_pct - 1e-9 <= ratio_pct <= high_pct + 1e-9:
        return 0
    delta_pct = (low_pct - ratio_pct) if ratio_pct < low_pct else (ratio_pct - high_pct)
    # 1 step per 5 percentage points outside the band; the `- 1e-9` lets
    # an exact 5%-step (delta_pct == 5.0) resolve to 1 step, not 2.
    steps = math.ceil(delta_pct / 5.0 - 1e-9)
    return max(WORD_COUNT_PENALTY_CAP, -steps)


def in_word_band(actual: int, target: int) -> bool:
    """True iff `actual` is inside [80%, 110%] of `target`."""
    return word_count_penalty(actual, target) == 0


__all__ = [
    "WORD_COUNT_BAND_HIGH",
    "WORD_COUNT_BAND_LOW",
    "WORD_COUNT_PENALTY_CAP",
    "WORD_COUNT_TARGETS",
    "count_words",
    "in_word_band",
    "word_count_penalty",
]
