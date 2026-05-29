"""Text utilities shared by the text-grading drills (dictation, gap-fill).

Pure stdlib. Normalization is accent- and case-insensitive so a learner
isn't penalized for a missing diacritic in a dictation transcription
(the diacritic check is a separate, finer signal the error classifier
surfaces, not a correctness gate).
"""

from __future__ import annotations

import re
import unicodedata

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def strip_accents(text: str) -> str:
    """Remove combining diacritics (é → e, ç → c)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_token(token: str) -> str:
    """Lowercase + accent-strip a single token for lenient comparison."""
    return strip_accents(token.casefold())


def tokenize(text: str) -> list[str]:
    """Split text into word tokens (drops punctuation/whitespace)."""
    return _WORD_RE.findall(text)


def normalized_tokens(text: str) -> list[str]:
    """Tokenize then normalize each token."""
    return [normalize_token(t) for t in tokenize(text)]


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein word-error-rate of `hypothesis` against `reference`.

    WER = (substitutions + insertions + deletions) / len(reference words).
    Comparison is accent- and case-insensitive. An empty reference with a
    non-empty hypothesis yields 1.0; two empty strings yield 0.0.

    Example:
        >>> word_error_rate("le chat dort", "le chat dort")
        0.0
        >>> word_error_rate("le chat dort", "le chien dort")  # 1 sub / 3
        0.3333333333333333

    Complexity: O(len(ref) * len(hyp)) time, O(len(hyp)) space.
    """
    ref = normalized_tokens(reference)
    hyp = normalized_tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0

    # Standard word-level edit distance (DP, two rows).
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        curr = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, start=1):
            cost = 0 if r == h else 1
            curr[j] = min(
                prev[j] + 1,  # deletion
                curr[j - 1] + 1,  # insertion
                prev[j - 1] + cost,  # substitution / match
            )
        prev = curr
    return prev[len(hyp)] / len(ref)


__all__ = [
    "normalize_token",
    "normalized_tokens",
    "strip_accents",
    "tokenize",
    "word_error_rate",
]
