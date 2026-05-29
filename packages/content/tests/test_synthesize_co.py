"""Tests for `tcf_accel_content.synthesize.co.synthesize_co_item`."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tcf_accel.schemas import COContent, Item, Speaker
from tcf_accel_content.cefr.classify import FakeCEFRClassifier
from tcf_accel_content.quality.gate import phase3_foundation_checks, run_gate
from tcf_accel_content.synthesize.co import (
    SYNTHESIZER_VERSION,
    COSynthesisInput,
    synthesize_co_item,
)

_TRANSCRIPT = (
    "Ce matin, plusieurs collègues se sont retrouvés au bureau pour préparer "
    "la présentation de la semaine prochaine. Ils ont discuté du calendrier, "
    "des responsabilités, et de la stratégie de communication."
)


def _input(*, seed: int = 0, source_id: str = "clip-1") -> COSynthesisInput:
    return COSynthesisInput(
        transcript=_TRANSCRIPT,
        audio_local_path="data/cache/audio/test.wav",
        duration_s=42.5,
        accent="fr-CA",
        register="standard",
        source="common_voice_fr_v17",
        source_id=source_id,
        license="CC0-1.0",
        ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
        speakers=(Speaker(label="Speaker A", accent="fr-CA"),),
        seed=seed,
    )


def test_synth_produces_valid_pydantic_item() -> None:
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    assert Item.model_validate(cand.item.model_dump()) == cand.item


def test_synth_emits_co_module() -> None:
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.module == "CO"
    assert isinstance(cand.item.content, COContent)


def test_synth_carries_transcript_verbatim() -> None:
    """Master prompt §6.3 invariant: the transcript is authoritative,
    never LLM-mutated. The synthesizer round-trips it unchanged."""
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.content.transcript == _TRANSCRIPT  # type: ignore[union-attr]


def test_synth_is_deterministic_for_same_input() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_co_item(_input(seed=7), classifier=clf)
    b = synthesize_co_item(_input(seed=7), classifier=clf)
    assert a.item.id == b.item.id
    assert a.item.model_dump() == b.item.model_dump()


def test_synth_differs_on_seed() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_co_item(_input(seed=1), classifier=clf)
    b = synthesize_co_item(_input(seed=2), classifier=clf)
    assert a.item.id != b.item.id


def test_synth_differs_on_source_id() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_co_item(_input(source_id="x"), classifier=clf)
    b = synthesize_co_item(_input(source_id="y"), classifier=clf)
    assert a.item.id != b.item.id


def test_synth_records_synthesizer_version_in_provenance() -> None:
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.provenance.synthesizer_version == SYNTHESIZER_VERSION
    assert cand.item.provenance.llm_prompt_hash is not None
    assert len(cand.item.provenance.llm_prompt_hash) == 64


def test_synth_accent_and_register_pass_through() -> None:
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.content.accent == "fr-CA"  # type: ignore[union-attr]
    assert cand.item.content.register == "standard"  # type: ignore[union-attr]


def test_synth_tags_accent_and_register_in_metadata() -> None:
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    assert "accent_fr-CA" in cand.item.metadata.tags
    assert "register_standard" in cand.item.metadata.tags


def test_synth_emits_four_options_length_balanced() -> None:
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    options = cand.item.content.questions[0].options  # type: ignore[union-attr]
    assert len(options) == 4
    assert len({o.id for o in options}) == 4
    lengths = [len(o.text.split()) for o in options]
    assert len(set(lengths)) == 1, f"option lengths not balanced: {lengths}"


def test_synth_passes_foundation_gate() -> None:
    """The CO foundation item runs the same gate as CE (length-balance
    P1 + license-compatible P0); both must pass."""
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    report = run_gate(cand.item, phase3_foundation_checks())
    assert report.verdict == "pass", [
        (c.name, c.detail) for c in report.checks if not c.passed
    ]


def test_synth_rejects_zero_duration() -> None:
    bad = COSynthesisInput(
        transcript=_TRANSCRIPT,
        audio_local_path="data/cache/audio/test.wav",
        duration_s=0.5,
        accent="fr-FR", register="standard",
        source="x", source_id="1", license="CC0-1.0",
        ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="duration_s"):
        synthesize_co_item(bad, classifier=FakeCEFRClassifier())


def test_synth_rejects_too_long_duration() -> None:
    bad = COSynthesisInput(
        transcript=_TRANSCRIPT,
        audio_local_path="data/cache/audio/test.wav",
        duration_s=601.0,
        accent="fr-FR", register="standard",
        source="x", source_id="1", license="CC0-1.0",
        ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="duration_s"):
        synthesize_co_item(bad, classifier=FakeCEFRClassifier())


def test_synth_rejects_empty_transcript() -> None:
    bad = COSynthesisInput(
        transcript="   ",
        audio_local_path="data/cache/audio/test.wav",
        duration_s=10.0,
        accent="fr-FR", register="standard",
        source="x", source_id="1", license="CC0-1.0",
        ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="transcript"):
        synthesize_co_item(bad, classifier=FakeCEFRClassifier())


def test_synth_co_acoustic_present_when_all_features_given() -> None:
    cand = synthesize_co_item(
        COSynthesisInput(
            transcript=_TRANSCRIPT,
            audio_local_path="data/cache/audio/test.wav",
            duration_s=30.0,
            accent="fr-FR", register="standard",
            source="x", source_id="1", license="CC0-1.0",
            ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
            speech_rate_wpm=145.0,
            lexical_density=0.62,
            n_speakers_diarized=2,
            noisiness_proxy=0.18,
        ),
        classifier=FakeCEFRClassifier(),
    )
    acoustic = cand.item.metadata.co_acoustic
    assert acoustic is not None
    assert acoustic["speech_rate_wpm"] == pytest.approx(145.0)
    assert acoustic["n_speakers_diarized"] == pytest.approx(2.0)


def test_synth_co_acoustic_absent_when_features_partial() -> None:
    """Partial acoustic features are dropped; no half-truth in the audit."""
    cand = synthesize_co_item(
        COSynthesisInput(
            transcript=_TRANSCRIPT,
            audio_local_path="data/cache/audio/test.wav",
            duration_s=30.0,
            accent="fr-FR", register="standard",
            source="x", source_id="1", license="CC0-1.0",
            ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
            speech_rate_wpm=145.0,
            # Other three features omitted on purpose.
        ),
        classifier=FakeCEFRClassifier(),
    )
    assert cand.item.metadata.co_acoustic is None


def test_synth_is_not_marked_synthetic() -> None:
    """CO transcripts/audio are real evidence; only the question is
    synthesized (ADR-0021 distinction)."""
    cand = synthesize_co_item(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.synthetic is False


def test_synth_classifier_drives_cefr_level() -> None:
    """The text-CEFR classification of the transcript becomes the
    item's cefr_level (no acoustic adjustment in foundation impl)."""
    clf = FakeCEFRClassifier()
    pred = clf.classify(_TRANSCRIPT)
    cand = synthesize_co_item(_input(), classifier=clf)
    assert cand.item.cefr_level == pred.level
    md = cand.item.metadata
    assert md.cefr_confidence == pytest.approx(pred.confidence)
