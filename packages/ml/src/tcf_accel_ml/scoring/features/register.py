"""Familier ↔ soutenu register scorer.

Returns a value in `[-1, +1]`:

- `-1`: heavily familier — contractions, slang, broken auxiliaries.
- ` 0`: neutral / standard.
- `+1`: heavily soutenu — subjunctive, complex connectors, lexical
  sophistication.

The scorer counts markers in each pole, normalizes by token count, and
maps via tanh so a few extra markers do not saturate the score.
"""

from __future__ import annotations

import math
from typing import Final

# Familier markers — common L1-influenced or oral-register tokens.
_FAMILIER_MARKERS: Final[frozenset[str]] = frozenset({
    "ben", "bah", "ouais", "nan", "hein", "quoi", "voilà",
    "du coup", "carrément", "trop", "genre", "grave",
    "machin", "truc", "chose", "vachement", "super",
    "j'ai trop", "c'est trop", "y a", "y'a", "ya",
})

# Soutenu markers — formal register, complex connectors, subjunctive
# auxiliaries, less-frequent vocab.
_SOUTENU_MARKERS: Final[frozenset[str]] = frozenset({
    "néanmoins", "toutefois", "cependant", "par ailleurs",
    "en outre", "de surcroît", "de surcroit", "dès lors",
    "force est de", "il convient", "il s'avère", "il appert",
    "nonobstant", "à l'instar", "en l'occurrence",
    "par conséquent", "c'est pourquoi", "en définitive",
    "suite à quoi", "qu'il en soit", "ne saurait", "ne sauraient",
})

# Single contraction patterns that score familier.
_FAMILIER_CONTRACTIONS: Final[tuple[str, ...]] = (
    "j'sais", "j'pense", "j'crois", "t'as", "t'es",
    "c'est pas", "j'ai pas", "y'a", "y a pas",
)


def _count_phrase_hits(text_lower: str, phrases: frozenset[str] | tuple[str, ...]) -> int:
    hits = 0
    for phrase in phrases:
        if not phrase:
            continue
        start = 0
        while True:
            idx = text_lower.find(phrase, start)
            if idx == -1:
                break
            hits += 1
            start = idx + len(phrase)
    return hits


def register_score(text: str) -> float:
    """Familier↔soutenu register score in `[-1, +1]`.

    Example:
        >>> register_score("Ben du coup voilà quoi")  # familier
        -1.0
        >>> register_score("Nonobstant les apparences, il convient de noter ceci.")  # soutenu
        1.0
        >>> register_score("Bonjour le monde.")
        0.0

    Complexity: O(len(text)).
    """
    if not text:
        return 0.0
    lower = text.casefold()
    n_tokens = max(1, len(text.split()))
    familier_hits = (
        _count_phrase_hits(lower, _FAMILIER_MARKERS)
        + _count_phrase_hits(lower, _FAMILIER_CONTRACTIONS)
    )
    soutenu_hits = _count_phrase_hits(lower, _SOUTENU_MARKERS)
    raw = (soutenu_hits - familier_hits) / max(1.0, n_tokens / 50.0)
    return float(math.tanh(raw))


__all__ = ["register_score"]
