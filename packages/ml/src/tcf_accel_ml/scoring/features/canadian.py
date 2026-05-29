"""Canadian-French lexicon density.

The TCF Canada's EE rubric rewards Canadian-context integration in
Tasks 2 & 3. We approximate it by counting tokens that match a small
curated lexicon of Canadian-French markers (province names, frequent
canadianisms, federal/provincial institutions).

The lexicon is intentionally small (~100 entries) and versioned: a bump
to the list is an ADR-grade change (R-042 in the risk register).

The density is `(canadian_token_count / total_tokens)`, clamped to
[0, 1].
"""

from __future__ import annotations

from typing import Final

# v1 Canadian-French lexicon. Grouped by domain for readability.
# Bump `_LEXICON_VERSION` whenever this list changes.
_LEXICON_VERSION: Final[str] = "fr-CA.v1"

_LEXICON: Final[frozenset[str]] = frozenset({
    # Province / city
    "québec", "quebec", "ontario", "montréal", "montreal", "toronto",
    "ottawa", "vancouver", "calgary", "edmonton", "winnipeg",
    "manitoba", "saskatchewan", "alberta", "colombie-britannique",
    "nouveau-brunswick", "nouvelle-écosse", "nouvelle-ecosse",
    "île-du-prince-édouard", "terre-neuve", "yukon", "nunavut",
    "territoires du nord-ouest", "acadie", "gaspésie", "abitibi",
    # Federal / provincial institutions
    "ircc", "régie", "regie", "scc", "rcmp", "grc", "loi 101",
    "charte canadienne", "charte de la langue", "scc", "office québécois",
    "office quebecois", "société canadienne", "société canadienne",
    "radio-canada", "cbc", "csst", "cnesst", "ramq", "service canada",
    # Canadianisms (frequent)
    "magasiner", "stationnement", "fin de semaine", "courriel",
    "déjeuner", "dîner", "souper", "char", "blonde", "chum",
    "tuque", "polar", "poutine", "bienvenue",
    # Civic / immigration
    "résident permanent", "citoyenneté canadienne", "tcf canada",
    "nclc", "clb", "immigration canada", "ircc",
})


def canadian_lexicon_density(text: str) -> float:
    """Share of tokens matching the Canadian-French lexicon.

    Single-word tokens are matched exactly; multi-word entries are
    matched as case-folded substrings (counted as one canadian-token
    hit each, with the word-count contribution being the number of
    words in the phrase).

    Example:
        >>> canadian_lexicon_density("Je vis à Montréal et je travaille à Québec.")  # 2 / 9
        0.2222222222222222
        >>> canadian_lexicon_density("Hello world")
        0.0
        >>> canadian_lexicon_density("")
        0.0

    Complexity: O(len(text) + n_tokens).
    """
    if not text:
        return 0.0
    lower = text.casefold()
    tokens = lower.split()
    n_tokens = len(tokens)
    if n_tokens == 0:
        return 0.0

    hits = 0
    # Single-word lexicon hits.
    for tok in tokens:
        clean = tok.strip(".,;:!?\"'()«»“”")
        if clean in _LEXICON:
            hits += 1
    # Multi-word lexicon hits.
    for entry in _LEXICON:
        if " " in entry:
            start = 0
            while True:
                idx = lower.find(entry, start)
                if idx == -1:
                    break
                hits += 1
                start = idx + len(entry)
    density = hits / n_tokens
    return min(1.0, density)


def lexicon_version() -> str:
    """Versioned lexicon identifier (audit tracks this per release)."""
    return _LEXICON_VERSION


__all__ = ["canadian_lexicon_density", "lexicon_version"]
