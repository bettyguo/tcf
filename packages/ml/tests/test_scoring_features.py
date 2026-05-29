"""Feature extractor unit tests (Phase 7).

Covers `WritingFeatures` / `SpeakingFeatures` extractors and the
canadian / register / connector building blocks.
"""

from __future__ import annotations

from tcf_accel_ml.scoring.features.canadian import canadian_lexicon_density
from tcf_accel_ml.scoring.features.connectors import (
    discourse_marker_counts,
    distinct_discourse_categories,
)
from tcf_accel_ml.scoring.features.errors import detect_errors
from tcf_accel_ml.scoring.features.register import register_score
from tcf_accel_ml.scoring.features.speaking import extract_speaking_features
from tcf_accel_ml.scoring.features.writing import (
    WritingFeatures,
    extract_writing_features,
)


# ─── WritingFeatures ─────────────────────────────────────────────


def test_writing_features_zero_vector_for_empty() -> None:
    f = extract_writing_features("")
    assert f.word_count == 0
    assert f.type_token_ratio == 0.0
    assert f.moving_average_ttr_25 == 0.0
    assert f.error_density_per_100w == 0.0


def test_writing_features_basic_counts() -> None:
    text = "Bonjour le monde. Comment allez-vous aujourd'hui?"
    f = extract_writing_features(text)
    assert f.word_count >= 6
    assert 0.0 < f.type_token_ratio <= 1.0
    assert f.mean_sentence_length > 0.0


def test_writing_features_mattr_more_stable_than_ttr_for_long_text() -> None:
    # A 100-word repeated chunk has low raw TTR but the MATTR-25
    # remains positive since within each window the diversity
    # holds up.
    text = "Le chat dort. " * 30
    f = extract_writing_features(text)
    assert f.type_token_ratio < 0.2
    assert f.moving_average_ttr_25 > f.type_token_ratio


def test_writing_features_vector_length_is_stable() -> None:
    # Stable feature-order is a calibrator contract — pin the size.
    f = extract_writing_features("Bonjour le monde.")
    assert len(f.as_vector()) == 14


def test_writing_features_never_raises_on_unicode_or_punctuation() -> None:
    # Defensive: weird inputs must not raise.
    for text in ("", "   ", "🙂🎉", "...,,,;;;", "à é è ê ç ô œ"):
        extract_writing_features(text)


# ─── Discourse markers ───────────────────────────────────────────


def test_discourse_markers_count_and_categorise() -> None:
    text = "Et donc, par ailleurs, enfin il faut conclure. Cependant, c'est dur."
    total, by_cat = discourse_marker_counts(text)
    assert total >= 4
    # at least: addition (et, par ailleurs), consequence (donc), conclusion (enfin), contrast (cependant)
    assert by_cat["addition"] >= 2
    assert by_cat["consequence"] >= 1
    assert by_cat["conclusion"] >= 1
    assert by_cat["contrast"] >= 1


def test_distinct_categories_one_for_repeated_marker() -> None:
    assert distinct_discourse_categories("et et et et et") == 1


def test_distinct_categories_zero_for_no_markers() -> None:
    assert distinct_discourse_categories("blah blah blah") == 0


# ─── Register score ──────────────────────────────────────────────


def test_register_score_in_bounds() -> None:
    assert -1.0 <= register_score("Bonjour le monde.") <= 1.0


def test_register_score_familier_is_negative() -> None:
    s = register_score("Ben du coup voilà quoi machin truc")
    assert s < 0.0


def test_register_score_soutenu_is_positive() -> None:
    s = register_score(
        "Nonobstant les apparences, il convient de souligner que cela ne saurait être ignoré.",
    )
    assert s > 0.0


def test_register_score_empty_is_neutral() -> None:
    assert register_score("") == 0.0


# ─── Canadian lexicon ────────────────────────────────────────────


def test_canadian_lexicon_density_in_bounds() -> None:
    assert 0.0 <= canadian_lexicon_density("Hello world") <= 1.0


def test_canadian_lexicon_density_zero_for_irrelevant_text() -> None:
    assert canadian_lexicon_density("hello world test foo bar") == 0.0


def test_canadian_lexicon_density_positive_for_quebec_mention() -> None:
    d = canadian_lexicon_density("Je vis à Montréal et je travaille à Québec.")
    assert d > 0.0


# ─── Heuristic error detector ────────────────────────────────────


def test_detect_errors_finds_si_aurais() -> None:
    errors = detect_errors("Si j'aurais le choix, je partirais demain.")
    types = {e.error_type for e in errors}
    assert "tense" in types
    spans = [(e.span_start, e.span_end) for e in errors if e.error_type == "tense"]
    assert spans


def test_detect_errors_finds_wrong_auxiliary() -> None:
    errors = detect_errors("J'ai allé au marché ce matin.")
    types = {e.error_type for e in errors}
    assert "agreement" in types


def test_detect_errors_finds_gender_un_voiture() -> None:
    errors = detect_errors("J'ai acheté un voiture rouge.")
    types = {e.error_type for e in errors}
    assert "agreement" in types


def test_detect_errors_empty_for_empty_input() -> None:
    assert detect_errors("") == []


def test_detect_errors_dedupes_overlapping_annotations() -> None:
    # Two calls on the same text yield identical-length output (no duplicates).
    text = "Si j'aurais. Si j'aurais. Si j'aurais."
    a = detect_errors(text)
    b = detect_errors(text)
    assert len(a) == len(b)
    # Three distinct occurrences => three distinct annotations (different spans).
    assert len({(e.span_start, e.span_end) for e in a}) == 3


# ─── SpeakingFeatures ────────────────────────────────────────────


def test_speaking_features_no_signal_marks_insufficient_data() -> None:
    f = extract_speaking_features(
        transcript="Bonjour le monde.", duration_s=2.0, asr_mean_confidence=0.9,
    )
    assert f.pronunciation_display_label == "insufficient_data"
    assert f.duration_s == 2.0


def test_speaking_features_wpm_computed_correctly() -> None:
    # 3 words in 1 second → 180 wpm.
    f = extract_speaking_features(
        transcript="bonjour le monde", duration_s=1.0, asr_mean_confidence=0.9,
    )
    assert abs(f.wpm - 180.0) < 0.1


def test_speaking_features_counts_fillers() -> None:
    f = extract_speaking_features(
        transcript="euh ben donc euh voilà", duration_s=60.0, asr_mean_confidence=0.9,
    )
    # 3 fillers in 1 minute → 3.0 per minute.
    assert f.filler_count_per_minute >= 2.0
