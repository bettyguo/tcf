"""Pause detection from forced-alignment timestamps.

A pause is any silence ≥ `PAUSE_THRESHOLD_MS` (default 200 ms) between
consecutive phoneme alignments. Computed from the MFA alignment, not
the audio waveform — this keeps the analyzer dependency-free and lets
the stub aligner exercise the same pipeline path as the real MFA.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import Final

from tcf_accel_ml.alignment.mfa import PhonemeAlignment

PAUSE_THRESHOLD_S: Final[float] = 0.200  # 200 ms


@dataclass(frozen=True)
class Pause:
    """A detected silence between two aligned phonemes."""

    start_s: float
    end_s: float

    @property
    def duration_s(self) -> float:
        """Pause duration in seconds."""
        return max(0.0, self.end_s - self.start_s)


def detect_pauses(
    alignments: list[PhonemeAlignment],
    *,
    threshold_s: float = PAUSE_THRESHOLD_S,
) -> list[Pause]:
    """Return pauses ≥ `threshold_s` between consecutive phonemes.

    Pauses *before* the first phoneme and *after* the last are excluded
    — those are leading/trailing silence, not pauses *inside* the
    utterance.

    Example:
        >>> from tcf_accel_ml.alignment.mfa import PhonemeAlignment
        >>> a = PhonemeAlignment(phoneme="a", start_s=0.0, end_s=0.5, confidence=1.0)
        >>> b = PhonemeAlignment(phoneme="b", start_s=0.8, end_s=1.0, confidence=1.0)
        >>> c = PhonemeAlignment(phoneme="c", start_s=1.0, end_s=1.2, confidence=1.0)
        >>> [p.duration_s for p in detect_pauses([a, b, c])]
        [0.30000000000000004]

    Complexity: O(len(alignments)).
    """
    pauses: list[Pause] = []
    for prev, nxt in pairwise(alignments):
        gap = nxt.start_s - prev.end_s
        if gap >= threshold_s:
            pauses.append(Pause(start_s=prev.end_s, end_s=nxt.start_s))
    return pauses


def summarize_pauses(pauses: list[Pause]) -> tuple[int, float]:
    """Return `(count, mean_pause_ms)`. Mean is 0.0 when count is 0."""
    if not pauses:
        return 0, 0.0
    total_ms = sum(p.duration_s for p in pauses) * 1000.0
    return len(pauses), total_ms / len(pauses)


__all__ = ["PAUSE_THRESHOLD_S", "Pause", "detect_pauses", "summarize_pauses"]
