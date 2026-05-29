"""`WritingFeatures` extractor.

Pure-Python, deterministic, importable in a clean venv. Computes the
load-bearing rubric feature vector from a UTF-8 text input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from tcf_accel_ml.scoring.features.canadian import canadian_lexicon_density
from tcf_accel_ml.scoring.features.connectors import discourse_marker_counts
from tcf_accel_ml.scoring.features.errors import detect_errors
from tcf_accel_ml.scoring.features.register import register_score

_SENTENCE_BREAK: Final[re.Pattern[str]] = re.compile(r"[.!?]+")
_WORD_BREAK: Final[re.Pattern[str]] = re.compile(r"[^\W\d_]+", re.UNICODE)

#: French verb endings that mark a subjunctive present (3rd person sg/pl).
#: Approximate; the heuristic is enough to *count* subjunctive use, not
#: to fully parse it. The risk of double-counting is bounded by being
#: tied to a small marker set ("que je", "que tu", "que il/elle…", etc).
_SUBJUNCTIVE_TRIGGERS: Final[tuple[str, ...]] = (
    "que je ", "que tu ", "qu'il ", "qu'elle ", "qu'on ",
    "que nous ", "que vous ", "qu'ils ", "qu'elles ",
    "bien que ", "afin que ", "avant que ", "pour que ",
    "à moins que ", "il faut que ",
)

_CONDITIONAL_ENDINGS: Final[tuple[str, ...]] = (
    "rais", "rait", "rions", "riez", "raient",
)

_PASSIVE_TRIGGERS: Final[tuple[str, ...]] = (
    "est ", "sont ", "était ", "étaient ", "sera ", "seront ",
    "a été ", "ont été ", "avait été ", "avaient été ",
)


@dataclass(frozen=True)
class WritingFeatures:
    """Feature vector consumed by the EE rubric calibrator.

    All fields are bounded; an empty input yields a zero-vector.
    """

    word_count: int
    type_token_ratio: float
    moving_average_ttr_25: float
    mean_sentence_length: float
    discourse_marker_count: int
    discourse_marker_density_per_100w: float
    distinct_discourse_categories: int
    error_density_per_100w: float
    flesch_reading_ease_fr: float
    canadian_lexicon_density: float
    register_score: float
    subjunctive_count: int
    conditional_count: int
    passive_count: int

    def as_vector(self) -> list[float]:
        """Stable feature order for the calibrator. Do not reorder."""
        return [
            float(self.word_count),
            self.type_token_ratio,
            self.moving_average_ttr_25,
            self.mean_sentence_length,
            float(self.discourse_marker_count),
            self.discourse_marker_density_per_100w,
            float(self.distinct_discourse_categories),
            self.error_density_per_100w,
            self.flesch_reading_ease_fr,
            self.canadian_lexicon_density,
            self.register_score,
            float(self.subjunctive_count),
            float(self.conditional_count),
            float(self.passive_count),
        ]

    @classmethod
    def zero(cls) -> "WritingFeatures":
        """A neutral-zero feature vector for the empty / no-text path."""
        return cls(
            word_count=0,
            type_token_ratio=0.0,
            moving_average_ttr_25=0.0,
            mean_sentence_length=0.0,
            discourse_marker_count=0,
            discourse_marker_density_per_100w=0.0,
            distinct_discourse_categories=0,
            error_density_per_100w=0.0,
            flesch_reading_ease_fr=0.0,
            canadian_lexicon_density=0.0,
            register_score=0.0,
            subjunctive_count=0,
            conditional_count=0,
            passive_count=0,
        )


def _moving_average_ttr(words: list[str], window: int = 25) -> float:
    """Moving-average TTR — Covington & McFall 2010.

    A 25-word window slides across the text; per-window TTR is averaged.
    For texts shorter than the window, falls back to raw TTR.
    """
    n = len(words)
    if n == 0:
        return 0.0
    lower = [w.casefold() for w in words]
    if n <= window:
        return len(set(lower)) / n
    total = 0.0
    n_windows = n - window + 1
    for i in range(n_windows):
        chunk = lower[i : i + window]
        total += len(set(chunk)) / window
    return total / n_windows


def _flesch_reading_ease_fr(*, n_sentences: int, n_words: int, n_syllables: int) -> float:
    """Approximate Flesch reading-ease, French adaptation.

    Formula (Kandel & Moles 1958 adaptation):
        FRE_fr = 207 − 1.015 × (words/sentences) − 73.6 × (syllables/words)

    Bounded to a sensible [0, 130] band; an empty input returns 0.
    """
    if n_sentences == 0 or n_words == 0:
        return 0.0
    ws = n_words / n_sentences
    spw = n_syllables / n_words
    score = 207.0 - 1.015 * ws - 73.6 * spw
    return max(0.0, min(130.0, score))


def _syllables_french(word: str) -> int:
    """Rough French syllable count: count vowel groups in the word."""
    vowels = set("aeiouyàâäéèêëîïôöùûüœæ")
    n = 0
    prev_was_vowel = False
    for ch in word.casefold():
        is_vowel = ch in vowels
        if is_vowel and not prev_was_vowel:
            n += 1
        prev_was_vowel = is_vowel
    return max(1, n)


def _count_phrase_occurrences(lower: str, phrases: tuple[str, ...]) -> int:
    n = 0
    for phrase in phrases:
        n += lower.count(phrase)
    return n


def _count_conditional(words: list[str]) -> int:
    """Count words ending in a conditional inflection."""
    return sum(
        1
        for w in words
        if any(w.casefold().endswith(end) for end in _CONDITIONAL_ENDINGS)
        and len(w) > 4
    )


def extract_writing_features(text: str) -> WritingFeatures:
    """Build a `WritingFeatures` from a raw text string.

    Pure function; deterministic; never raises. An empty input
    returns `WritingFeatures.zero()`.

    Example:
        >>> f = extract_writing_features("Bonjour le monde. Comment allez-vous?")
        >>> f.word_count
        6
        >>> 0.0 <= f.type_token_ratio <= 1.0
        True
    """
    if not text or not text.strip():
        return WritingFeatures.zero()

    words = _WORD_BREAK.findall(text)
    n_words = len(words)
    if n_words == 0:
        return WritingFeatures.zero()

    # Type-token ratios.
    lower_words = [w.casefold() for w in words]
    ttr = len(set(lower_words)) / n_words
    mattr = _moving_average_ttr(words)

    # Sentence stats.
    sentence_chunks = [s for s in _SENTENCE_BREAK.split(text) if s.strip()]
    n_sentences = max(1, len(sentence_chunks))
    mean_sentence_length = n_words / n_sentences

    # Discourse markers.
    dm_count, _by_cat = discourse_marker_counts(text)
    dm_density = (dm_count / n_words * 100.0) if n_words else 0.0
    distinct_categories = sum(1 for v in _by_cat.values() if v > 0)

    # Errors.
    errors = detect_errors(text)
    error_density = (len(errors) / n_words * 100.0) if n_words else 0.0

    # Reading ease.
    n_syllables = sum(_syllables_french(w) for w in words)
    fre = _flesch_reading_ease_fr(
        n_sentences=n_sentences, n_words=n_words, n_syllables=n_syllables,
    )

    # Verb-mood approximations.
    lower_text = text.casefold()
    subjunctive_count = _count_phrase_occurrences(lower_text, _SUBJUNCTIVE_TRIGGERS)
    conditional_count = _count_conditional(words)
    passive_count = _count_phrase_occurrences(lower_text, _PASSIVE_TRIGGERS)

    return WritingFeatures(
        word_count=n_words,
        type_token_ratio=ttr,
        moving_average_ttr_25=mattr,
        mean_sentence_length=mean_sentence_length,
        discourse_marker_count=dm_count,
        discourse_marker_density_per_100w=dm_density,
        distinct_discourse_categories=distinct_categories,
        error_density_per_100w=error_density,
        flesch_reading_ease_fr=fre,
        canadian_lexicon_density=canadian_lexicon_density(text),
        register_score=register_score(text),
        subjunctive_count=subjunctive_count,
        conditional_count=conditional_count,
        passive_count=passive_count,
    )


__all__ = ["WritingFeatures", "extract_writing_features"]
