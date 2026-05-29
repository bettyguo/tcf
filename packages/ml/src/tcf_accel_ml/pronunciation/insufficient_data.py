"""The insufficient-data gate (`phase5_design.md §5.2`, §5.3).

Maps the pipeline's raw signals (PER, ASR confidence, utterance
duration, aligned phoneme count) to a `PronunciationDisplayLabel`.

The `"insufficient_data"` path is the refuse-to-predict guarantee:
when any of the three input quality predicates fails, the
`PronunciationSignal` ships a non-numeric label and the planner
ignores the row's score (`phase5_audit.md §8`). This is structurally
the same shape as `SkillPosterior.confident` from Phase 4 (ADR-025):
honesty over precision.

The thresholds are tunable per release; the **shape** of the gate is
not — there is no path from a sub-2-second utterance to a "strong"
display label.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.pronunciation import PronunciationDisplayLabel

# Quality thresholds. Tunable per release; the structural property is
# the gate's existence, not the numbers (ADR-031).
INSUFFICIENT_DURATION_S: Final[float] = 2.0
INSUFFICIENT_ASR_CONFIDENCE: Final[float] = 0.50
INSUFFICIENT_PHONEMES: Final[int] = 8

# PER bands. PER ∈ [0, ∞) — under 10% is strong, under 20% fair.
DISPLAY_LABEL_PER_STRONG: Final[float] = 0.10
DISPLAY_LABEL_PER_FAIR: Final[float] = 0.20


def display_label_from(
    *,
    per: float,
    asr_mean_confidence: float,
    duration_s: float,
    n_phonemes_aligned: int,
) -> PronunciationDisplayLabel:
    """Map pipeline signals to a `PronunciationDisplayLabel`.

    Returns ``"insufficient_data"`` when any quality predicate fails
    (sub-2-second utterance, ASR confidence below 0.50, or fewer than 8
    aligned phonemes). Otherwise the PER is bucketed into
    ``strong``/``fair``/``weak``.

    Example:
        >>> display_label_from(per=0.05, asr_mean_confidence=0.9,
        ...                     duration_s=10.0, n_phonemes_aligned=30)
        'strong'
        >>> display_label_from(per=0.15, asr_mean_confidence=0.9,
        ...                     duration_s=10.0, n_phonemes_aligned=30)
        'fair'
        >>> display_label_from(per=0.30, asr_mean_confidence=0.9,
        ...                     duration_s=10.0, n_phonemes_aligned=30)
        'weak'
        >>> display_label_from(per=0.05, asr_mean_confidence=0.9,
        ...                     duration_s=1.0, n_phonemes_aligned=30)
        'insufficient_data'

    Complexity: O(1).
    """
    if (
        duration_s < INSUFFICIENT_DURATION_S
        or asr_mean_confidence < INSUFFICIENT_ASR_CONFIDENCE
        or n_phonemes_aligned < INSUFFICIENT_PHONEMES
    ):
        return "insufficient_data"
    if per < DISPLAY_LABEL_PER_STRONG:
        return "strong"
    if per < DISPLAY_LABEL_PER_FAIR:
        return "fair"
    return "weak"


__all__ = [
    "DISPLAY_LABEL_PER_FAIR",
    "DISPLAY_LABEL_PER_STRONG",
    "INSUFFICIENT_ASR_CONFIDENCE",
    "INSUFFICIENT_DURATION_S",
    "INSUFFICIENT_PHONEMES",
    "display_label_from",
]
