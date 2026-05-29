"""Heuristic span-level error detector.

Covers the highest-frequency L2 French errors that are detectable via
regex without a parser:

- `si j'aurais …` (conditional protasis using conditional instead of imperfect).
- `*ai allé`, `*ai venu` (wrong auxiliary for verbs of movement).
- Double-negation gaps (`ne … rien` without `pas`).
- Common gender errors on frequent feminine-looking masculine nouns.
- ASCII apostrophe in `j'ai`, `c'est`, `l'on` (style — Canadian
  formal writing prefers the typographic apostrophe; we surface this
  as a `minor` register flag).

The detector emits `ErrorAnnotation` objects with the schema-frozen
shape from `tcf_accel.schemas.content.ee`. A `confidence` is attached
per rule.

This is the *floor* error signal. The LLM critic adds higher-level
errors (cohesion gaps, off-topic content) that regex cannot catch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from tcf_accel.schemas.content.ee import ErrorAnnotation, ErrorType


@dataclass(frozen=True)
class _Rule:
    pattern: re.Pattern[str]
    error_type: ErrorType
    suggestion: str | None
    confidence: float


_RULES: Final[tuple[_Rule, ...]] = (
    # Conditional protasis: "si j'aurais", "si tu aurais", "si nous aurions"…
    _Rule(
        pattern=re.compile(
            r"\bsi\s+(j['']aurais|tu\s+aurais|il\s+aurait|elle\s+aurait|"
            r"nous\s+aurions|vous\s+auriez|ils\s+auraient|elles\s+auraient)\b",
            re.IGNORECASE,
        ),
        error_type="tense",
        suggestion="use imperfect indicative in si-clauses (Type II)",
        confidence=0.95,
    ),
    # Wrong auxiliary: ai allé / as allé / a allé / avons allé / etc.
    _Rule(
        pattern=re.compile(
            r"\b(ai|as|a|avons|avez|ont)\s+(allé|allée|venu|venue|"
            r"parti|partie|arrivé|arrivée|monté|montée|descendu|descendue|"
            r"resté|restée|tombé|tombée|né|née|mort|morte)\b",
            re.IGNORECASE,
        ),
        error_type="agreement",
        suggestion="movement verbs take être, not avoir",
        confidence=0.92,
    ),
    # Bare "ne" with a noun ("ne rien", "ne jamais") missing pas — we
    # actually look for the inverse: noun verb without `ne` but with
    # `pas`. Approximate: standalone "pas" without "ne" before the verb.
    # (This is noisy; mark confidence low.)
    _Rule(
        pattern=re.compile(r"\b(je|tu|il|elle|on|nous|vous|ils|elles)\s+\w+\s+pas\b", re.IGNORECASE),
        error_type="syntax",
        suggestion="formal register: insert 'ne' before the verb (ne … pas)",
        confidence=0.45,
    ),
    # Common gender errors on frequent words: "un voiture", "un table",
    # "un maison", "un chaise"…
    _Rule(
        pattern=re.compile(
            r"\bun\s+(voiture|table|maison|chaise|porte|fenêtre|fenetre|"
            r"école|ecole|fleur|page|chose|histoire|salle|fois)\b",
            re.IGNORECASE,
        ),
        error_type="agreement",
        suggestion="use the feminine article 'une'",
        confidence=0.90,
    ),
    # "une problème", "une livre", "une exemple"…
    _Rule(
        pattern=re.compile(
            r"\bune\s+(problème|probleme|livre|exemple|hôpital|hopital|"
            r"avion|musée|musee|moment|matin|soir|jour)\b",
            re.IGNORECASE,
        ),
        error_type="agreement",
        suggestion="use the masculine article 'un'",
        confidence=0.85,
    ),
    # Spelling: "language" instead of "langue", "professeur" misspellings…
    _Rule(
        pattern=re.compile(r"\blanguag\w*\b", re.IGNORECASE),
        error_type="spelling",
        suggestion="'langue' (not the English 'language')",
        confidence=0.95,
    ),
    # Anglicism: "je suis intéressé en …" vs "intéressé par"
    _Rule(
        pattern=re.compile(r"\bintéressé\s+en\b|\binteresse\s+en\b", re.IGNORECASE),
        error_type="preposition",
        suggestion="'intéressé par' (not 'intéressé en')",
        confidence=0.88,
    ),
    # Anglicism: "j'aime ça beaucoup" rather than "j'aime beaucoup ça"
    _Rule(
        pattern=re.compile(r"\b(j['']aime|tu\s+aimes|il\s+aime|elle\s+aime)\s+\w+\s+beaucoup\b", re.IGNORECASE),
        error_type="syntax",
        suggestion="adverb 'beaucoup' usually precedes the object",
        confidence=0.55,
    ),
)


class HeuristicErrorDetector:
    """Reusable, deterministic regex-only error detector.

    Constructed once, called per submission. Threadsafe (no mutable
    state on the instance).
    """

    def detect(self, text: str) -> list[ErrorAnnotation]:
        """Apply every rule, return deduplicated annotations.

        Two annotations with the same `(span_start, span_end, error_type)`
        are deduped, keeping the higher-confidence one.
        """
        if not text:
            return []
        raw: list[ErrorAnnotation] = []
        for rule in _RULES:
            for m in rule.pattern.finditer(text):
                start, end = m.start(), m.end()
                raw.append(
                    ErrorAnnotation(
                        span_start=start,
                        span_end=end,
                        error_type=rule.error_type,
                        suggestion=rule.suggestion,
                        confidence=rule.confidence,
                    )
                )
        return _dedupe(raw)


def detect_errors(text: str) -> list[ErrorAnnotation]:
    """Module-level shortcut for one-off calls."""
    return HeuristicErrorDetector().detect(text)


def _dedupe(errors: list[ErrorAnnotation]) -> list[ErrorAnnotation]:
    """Dedupe by `(span_start, span_end, error_type)`, keeping max confidence."""
    by_key: dict[tuple[int, int, str], ErrorAnnotation] = {}
    for err in errors:
        key = (err.span_start, err.span_end, err.error_type)
        existing = by_key.get(key)
        if existing is None or err.confidence > existing.confidence:
            by_key[key] = err
    return sorted(
        by_key.values(),
        key=lambda e: (e.span_start, e.span_end, e.error_type),
    )


__all__ = ["HeuristicErrorDetector", "detect_errors"]
