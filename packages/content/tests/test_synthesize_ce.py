"""Tests for `tcf_accel_content.synthesize.ce.synthesize_ce_item`."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tcf_accel.schemas import CEContent, Item, QualityFlag
from tcf_accel_content.cefr.classify import FakeCEFRClassifier
from tcf_accel_content.synthesize.ce import (
    SYNTHESIZER_VERSION,
    CESynthesisInput,
    synthesize_ce_item,
)

_PASSAGE = (
    "Le matin, Marie se lève tôt et prend son café avant de partir au "
    "travail. Elle marche jusqu'à la station de métro, lit un livre, "
    "et arrive au bureau à neuf heures."
)


def _input(*, seed: int = 0, source_id: str = "1") -> CESynthesisInput:
    return CESynthesisInput(
        passage=_PASSAGE,
        genre="narrative",
        source="wikisource_fr",
        source_id=source_id,
        license="CC-BY-SA-4.0",
        ingested_at=datetime(2026, 5, 27, tzinfo=UTC),
        seed=seed,
    )


def test_synth_produces_valid_pydantic_item() -> None:
    clf = FakeCEFRClassifier()
    candidate = synthesize_ce_item(_input(), classifier=clf)
    # Pydantic-valid by construction; round-trip just confirms.
    round_tripped = Item.model_validate(candidate.item.model_dump())
    assert round_tripped == candidate.item


def test_synth_emits_ce_module() -> None:
    candidate = synthesize_ce_item(_input(), classifier=FakeCEFRClassifier())
    assert candidate.item.module == "CE"
    assert isinstance(candidate.item.content, CEContent)
    assert candidate.item.content.genre == "narrative"


def test_synth_is_deterministic_for_same_input() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_ce_item(_input(seed=7), classifier=clf)
    b = synthesize_ce_item(_input(seed=7), classifier=clf)
    assert a.item.id == b.item.id
    assert a.item.model_dump() == b.item.model_dump()


def test_synth_differs_on_seed() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_ce_item(_input(seed=1), classifier=clf)
    b = synthesize_ce_item(_input(seed=2), classifier=clf)
    assert a.item.id != b.item.id


def test_synth_differs_on_source_id() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_ce_item(_input(source_id="1"), classifier=clf)
    b = synthesize_ce_item(_input(source_id="2"), classifier=clf)
    assert a.item.id != b.item.id


def test_synth_records_synthesizer_version_in_provenance() -> None:
    candidate = synthesize_ce_item(_input(), classifier=FakeCEFRClassifier())
    assert candidate.item.provenance.synthesizer_version == SYNTHESIZER_VERSION
    assert candidate.item.provenance.llm_prompt_hash is not None
    assert len(candidate.item.provenance.llm_prompt_hash) == 64  # sha256 hex


def test_synth_uses_classifier_for_cefr_level() -> None:
    candidate = synthesize_ce_item(_input(), classifier=FakeCEFRClassifier())
    # Foundation fakes always agree with themselves; the level is in range
    # and metadata carries the matching confidence and distribution.
    assert candidate.item.cefr_level in {"A1", "A2", "B1", "B2", "C1", "C2"}
    md = candidate.item.metadata
    assert md.cefr_confidence is not None
    assert 0.0 <= md.cefr_confidence <= 1.0
    assert md.cefr_distribution is not None
    assert md.cefr_distribution[candidate.item.cefr_level] == pytest.approx(
        md.cefr_confidence,
    )


def test_synth_emits_four_options_with_unique_ids() -> None:
    candidate = synthesize_ce_item(_input(), classifier=FakeCEFRClassifier())
    questions = candidate.item.content.questions  # type: ignore[union-attr]
    assert len(questions) == 1
    options = questions[0].options
    assert len(options) == 4
    assert len({o.id for o in options}) == 4
    assert questions[0].correct_option_id in {o.id for o in options}


def test_synth_options_pass_length_balance() -> None:
    """The synthesizer's option pool is length-balanced by design."""
    candidate = synthesize_ce_item(_input(), classifier=FakeCEFRClassifier())
    options = candidate.item.content.questions[0].options  # type: ignore[union-attr]
    lengths = [len(o.text.split()) for o in options]
    # All four options carry the same whitespace token count.
    assert len(set(lengths)) == 1


def test_synth_tags_metadata_for_audit() -> None:
    candidate = synthesize_ce_item(_input(), classifier=FakeCEFRClassifier())
    assert "foundation_synth" in candidate.item.metadata.tags


def test_synth_trace_carries_prompt_hash() -> None:
    candidate = synthesize_ce_item(_input(seed=42), classifier=FakeCEFRClassifier())
    assert candidate.trace.prompt_hash == candidate.item.provenance.llm_prompt_hash
    assert candidate.trace.seed == 42


def test_synth_does_not_pre_flag_synthetic() -> None:
    # Foundation items have synthesizer_version set but are NOT marked
    # synthetic=True — the passage is real (from a fixture source); only
    # the question is synthesized. ADR-0021 distinguishes the two.
    candidate = synthesize_ce_item(_input(), classifier=FakeCEFRClassifier())
    assert candidate.item.synthetic is False
    assert QualityFlag.SYNTHETIC not in candidate.item.quality_flags
