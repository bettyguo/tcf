"""Discourse-marker registry.

The set is grouped into 5 functional categories so the feature
extractor can report both raw count and `distinct_discourse_categories`
(a learner who uses six "et" but no other connector scores 1 category;
a learner who uses one each of et / mais / car / donc / enfin scores
5).

Phase 5's `score_ee` stub inlines a smaller seed (the `_CONNECTOR_SEED`
frozenset). Phase 7 supersedes it; the stub keeps its inline copy for
backwards compatibility so the worker is not coupled to ML import
order.
"""

from __future__ import annotations

from typing import Final

#: Category → markers. Multi-word markers ("par ailleurs") are matched
#: by exact substring (case-insensitive); single-word markers are
#: matched by tokenisation.
_DISCOURSE_MARKERS: Final[dict[str, tuple[str, ...]]] = {
    "addition": (
        "et", "aussi", "également", "puis", "ensuite",
        "de plus", "par ailleurs", "en outre", "de surcroît",
    ),
    "contrast": (
        "mais", "cependant", "néanmoins", "toutefois",
        "en revanche", "or", "pourtant", "malgré tout",
    ),
    "cause": (
        "car", "parce", "puisque", "comme", "étant donné",
        "en effet", "du fait",
    ),
    "consequence": (
        "donc", "ainsi", "alors", "par conséquent",
        "c'est pourquoi", "dès lors",
    ),
    "conclusion": (
        "enfin", "finalement", "en conclusion", "pour conclure",
        "en somme", "bref", "en définitive",
    ),
    "temporal": (
        "d'abord", "ensuite", "puis", "après", "avant",
        "ensuite", "lors", "tandis que",
    ),
}

_SINGLE_WORD_MARKERS: Final[dict[str, str]] = {
    word: cat
    for cat, words in _DISCOURSE_MARKERS.items()
    for word in words
    if " " not in word
}

_MULTI_WORD_MARKERS: Final[tuple[tuple[str, str], ...]] = tuple(
    (phrase.casefold(), cat)
    for cat, words in _DISCOURSE_MARKERS.items()
    for phrase in words
    if " " in phrase
)


def discourse_marker_counts(text: str) -> tuple[int, dict[str, int]]:
    """Count discourse markers + per-category breakdown.

    Returns `(total_count, per_category)`. Multi-word markers are
    matched against the casefolded full text; single-word markers are
    matched after tokenisation.

    Example:
        >>> total, by_cat = discourse_marker_counts(
        ...     "Et donc, par ailleurs, enfin il faut conclure."
        ... )
        >>> total
        4
        >>> sorted(by_cat)
        ['addition', 'conclusion', 'consequence']

    Complexity: O(len(text) + n_tokens × n_categories).
    """
    lower = text.casefold()
    per_category: dict[str, int] = {cat: 0 for cat in _DISCOURSE_MARKERS}

    # Multi-word markers — count overlap-free substring occurrences.
    for phrase, cat in _MULTI_WORD_MARKERS:
        if not phrase:
            continue
        start = 0
        while True:
            idx = lower.find(phrase, start)
            if idx == -1:
                break
            per_category[cat] += 1
            start = idx + len(phrase)

    # Single-word markers — tokenise on whitespace/punctuation.
    tokens = _tokenize(text)
    for tok in tokens:
        cat = _SINGLE_WORD_MARKERS.get(tok.casefold())
        if cat is not None:
            per_category[cat] += 1

    total = sum(per_category.values())
    return total, per_category


def distinct_discourse_categories(text: str) -> int:
    """Number of distinct discourse-marker categories used.

    A learner who deploys two markers from three categories scores 3.
    A learner who repeats "et" twelve times scores 1.

    Example:
        >>> distinct_discourse_categories("et et mais donc")
        3
        >>> distinct_discourse_categories("blah blah")
        0
    """
    _, per_category = discourse_marker_counts(text)
    return sum(1 for v in per_category.values() if v > 0)


def _tokenize(text: str) -> list[str]:
    """Whitespace + punctuation tokenisation; lowercase preserved on output."""
    cleaned = []
    cur: list[str] = []
    for ch in text:
        if ch.isalpha() or ch == "'":
            cur.append(ch)
        else:
            if cur:
                cleaned.append("".join(cur))
                cur = []
    if cur:
        cleaned.append("".join(cur))
    return cleaned


__all__ = [
    "discourse_marker_counts",
    "distinct_discourse_categories",
]
