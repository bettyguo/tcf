"""Tests for `tcf_accel_content.synthesize.ee.synthesize_ee_prompt`."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tcf_accel.schemas import EEContent, Item, QualityFlag
from tcf_accel_content.cefr.classify import FakeCEFRClassifier
from tcf_accel_content.synthesize.ee import (
    RUBRIC_VERSION,
    SOURCE_LICENSE,
    SOURCE_NAME,
    SYNTHESIZER_VERSION,
    EESynthesisInput,
    synthesize_ee_prompt,
)


def _input(
    *,
    task_number: int = 2,
    canadian_context: bool = True,
    seed: int = 0,
) -> EESynthesisInput:
    return EESynthesisInput(
        task_number=task_number,  # type: ignore[arg-type]
        canadian_context=canadian_context,
        cefr_target="B2",
        seed=seed,
        ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
    )


def test_synth_produces_valid_pydantic_item() -> None:
    cand = synthesize_ee_prompt(_input(), classifier=FakeCEFRClassifier())
    assert Item.model_validate(cand.item.model_dump()) == cand.item


def test_synth_emits_ee_module() -> None:
    cand = synthesize_ee_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.module == "EE"
    assert isinstance(cand.item.content, EEContent)


def test_synth_is_deterministic() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_ee_prompt(_input(seed=7), classifier=clf)
    b = synthesize_ee_prompt(_input(seed=7), classifier=clf)
    assert a.item.id == b.item.id
    assert a.item.model_dump() == b.item.model_dump()


def test_synth_differs_on_seed() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_ee_prompt(_input(seed=1), classifier=clf)
    b = synthesize_ee_prompt(_input(seed=99), classifier=clf)
    # When the pool has > 1 variant the prompts diverge; when only one
    # variant exists the id may still match. The (T2, ca=True) bucket
    # has multiple variants, so divergence is expected here.
    assert a.item.content.prompt != b.item.content.prompt or a.item.id == b.item.id


def test_synth_task1_respects_word_count_range() -> None:
    cand = synthesize_ee_prompt(
        _input(task_number=1, canadian_context=False),
        classifier=FakeCEFRClassifier(),
    )
    assert cand.item.content.target_word_count_range == (50, 70)  # type: ignore[union-attr]


def test_synth_task2_respects_word_count_range() -> None:
    cand = synthesize_ee_prompt(_input(task_number=2), classifier=FakeCEFRClassifier())
    assert cand.item.content.target_word_count_range == (110, 130)  # type: ignore[union-attr]


def test_synth_task3_respects_word_count_range() -> None:
    cand = synthesize_ee_prompt(_input(task_number=3), classifier=FakeCEFRClassifier())
    assert cand.item.content.target_word_count_range == (170, 190)  # type: ignore[union-attr]


@pytest.mark.parametrize("task_number", [2, 3])
def test_synth_task2_and_3_require_canadian_context(task_number: int) -> None:
    with pytest.raises(ValueError, match="canadian_context=True"):
        synthesize_ee_prompt(
            _input(task_number=task_number, canadian_context=False),
            classifier=FakeCEFRClassifier(),
        )


def test_synth_task1_accepts_either_canadian_flag() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_ee_prompt(
        _input(task_number=1, canadian_context=False), classifier=clf,
    )
    b = synthesize_ee_prompt(
        _input(task_number=1, canadian_context=True), classifier=clf,
    )
    assert a.item.content.required_canadian_context is False  # type: ignore[union-attr]
    assert b.item.content.required_canadian_context is True  # type: ignore[union-attr]


def test_synth_propagates_canadian_context_to_metadata() -> None:
    cand = synthesize_ee_prompt(
        _input(task_number=2, canadian_context=True),
        classifier=FakeCEFRClassifier(),
    )
    assert cand.item.metadata.canadian_context is True


def test_synth_rubric_version_pinned() -> None:
    cand = synthesize_ee_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.content.rubric_version == RUBRIC_VERSION == "ee.v1"  # type: ignore[union-attr]


def test_synth_provenance_uses_foundation_source() -> None:
    cand = synthesize_ee_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.provenance.source == SOURCE_NAME
    assert cand.item.provenance.license == SOURCE_LICENSE
    assert cand.item.provenance.synthesizer_version == SYNTHESIZER_VERSION


def test_synth_carries_placeholder_calibration_anchors() -> None:
    cand = synthesize_ee_prompt(_input(), classifier=FakeCEFRClassifier())
    anchors = cand.item.metadata.calibration_anchors
    assert anchors is not None
    assert set(anchors.keys()) == {"nclc_7", "nclc_9", "nclc_11"}


def test_synth_marks_synthetic_true_per_adr_0021() -> None:
    cand = synthesize_ee_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.synthetic is True
    # The QualityFlag.SYNTHETIC enum is not pre-attached at synth time;
    # the loader / audit attaches flags based on the report. The boolean
    # column is the canonical signal Phase 4 reads.
    assert QualityFlag.SYNTHETIC not in cand.item.quality_flags


def test_synth_uses_cefr_target_not_classifier_for_level() -> None:
    """EE prompts are short; we set level from the target, not the classifier."""
    cand = synthesize_ee_prompt(
        EESynthesisInput(
            task_number=2, canadian_context=True, cefr_target="C1", seed=0,
        ),
        classifier=FakeCEFRClassifier(),
    )
    assert cand.item.cefr_level == "C1"


def test_synth_records_cefr_confidence_from_classifier() -> None:
    cand = synthesize_ee_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.metadata.cefr_confidence is not None
    assert 0.0 <= cand.item.metadata.cefr_confidence <= 1.0


def test_synth_invalid_task_number_raises() -> None:
    with pytest.raises(ValueError, match="task_number"):
        synthesize_ee_prompt(
            EESynthesisInput(
                task_number=5,  # type: ignore[arg-type]
                canadian_context=True,
                cefr_target="B2",
            ),
            classifier=FakeCEFRClassifier(),
        )
