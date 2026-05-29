"""TCF Canada total_20 ↔ NCLC band lookup (ADR-036).

The TCF Canada uses a 6-band scale (1–6) per skill that maps to NCLC
through the official IRCC table. The rubric scorer outputs a finer
0–20 score; the report aggregates and emits an NCLC band per skill.

The lookup is **published**: the breakpoints are stable per release
and live in this module so a single grep finds them. A bump to this
table is an ADR-grade change (see ADR-036).
"""

from __future__ import annotations

from typing import Final

# 0–20 → NCLC band breakpoints. Each tuple is `(min_total_inclusive, nclc)`.
# A total_20 of 14 lands at NCLC 9 (the threshold most learners target).
# The TCF Canada → NCLC mapping is described in
# `04_LEARNER_MODEL.md §3.4`; the breakpoints here are the project's
# v1 mapping and are revisited per release (ADR-036).
_BAND_BREAKPOINTS: Final[tuple[tuple[int, int], ...]] = (
    (0, 3),
    (5, 4),
    (7, 5),
    (9, 6),
    (11, 7),
    (13, 8),
    (15, 9),
    (16, 10),
    (18, 11),
    (19, 12),
)


def nclc_from_total_20(total: float) -> int:
    """Map a 0–20 rubric total to an NCLC band 3..12.

    Example:
        >>> nclc_from_total_20(0)
        3
        >>> nclc_from_total_20(14)
        8
        >>> nclc_from_total_20(15)
        9
        >>> nclc_from_total_20(20)
        12

    Complexity: O(len(_BAND_BREAKPOINTS)) = O(10).
    """
    clamped = max(0.0, min(20.0, float(total)))
    nclc = _BAND_BREAKPOINTS[0][1]
    for threshold, band in _BAND_BREAKPOINTS:
        if clamped >= threshold:
            nclc = band
        else:
            break
    return nclc


__all__ = ["nclc_from_total_20"]
