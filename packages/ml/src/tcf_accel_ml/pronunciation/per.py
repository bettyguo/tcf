"""Phoneme Error Rate (`phase5_design.md §5.1`).

Levenshtein distance over phoneme sequences, normalized by the length
of the reference. Same algorithmic shape as the word-level WER in
`tcf_accel_sla.drills._text` — duplicated here because the two
packages must remain dependency-disjoint (`packages/ml` may not import
from `packages/sla`).

The phoneme alphabet itself is the caller's concern: in production the
sequences are IPA tokens emitted by the Montreal Forced Aligner; in
the stub-backed test paths they are the source-text characters. PER's
computation is alphabet-agnostic.
"""

from __future__ import annotations


def phoneme_error_rate(reference: list[str], hypothesis: list[str]) -> float:
    """Levenshtein word-error-rate over phoneme sequences.

    PER = (substitutions + insertions + deletions) / len(reference).
    Empty reference + empty hypothesis yields 0.0; empty reference with
    a non-empty hypothesis yields 1.0 (every emitted phoneme is an
    insertion against a zero-length target).

    Example:
        >>> phoneme_error_rate(["a", "b", "c"], ["a", "b", "c"])
        0.0
        >>> phoneme_error_rate(["a", "b", "c"], ["a", "x", "c"])  # 1 sub / 3
        0.3333333333333333
        >>> phoneme_error_rate(["a", "b"], ["a", "b", "c"])  # 1 ins / 2
        0.5

    Complexity: O(len(reference) * len(hypothesis)) time, O(len(hypothesis)) space.
    """
    if not reference:
        return 0.0 if not hypothesis else 1.0

    prev = list(range(len(hypothesis) + 1))
    for i, r in enumerate(reference, start=1):
        curr = [i] + [0] * len(hypothesis)
        for j, h in enumerate(hypothesis, start=1):
            cost = 0 if r == h else 1
            curr[j] = min(
                prev[j] + 1,  # deletion
                curr[j - 1] + 1,  # insertion
                prev[j - 1] + cost,  # substitution / match
            )
        prev = curr
    return prev[len(hypothesis)] / len(reference)


__all__ = ["phoneme_error_rate"]
