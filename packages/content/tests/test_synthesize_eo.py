"""Tests for `tcf_accel_content.synthesize.eo.synthesize_eo_prompt`."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tcf_accel.schemas import EOContent, Item
from tcf_accel_content.cefr.classify import FakeCEFRClassifier
from tcf_accel_content.synthesize.eo import (
    RUBRIC_VERSION,
    SOURCE_LICENSE,
    SOURCE_NAME,
    SYNTHESIZER_VERSION,
    EOSynthesisInput,
    synthesize_eo_prompt,
)


def _input(*, task_number: int = 1, seed: int = 0) -> EOSynthesisInput:
    return EOSynthesisInput(
        task_number=task_number,  # type: ignore[arg-type]
        cefr_target="B2",
        seed=seed,
        ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
    )


def test_synth_produces_valid_pydantic_item() -> None:
    cand = synthesize_eo_prompt(_input(), classifier=FakeCEFRClassifier())
    assert Item.model_validate(cand.item.model_dump()) == cand.item


def test_synth_emits_eo_module() -> None:
    cand = synthesize_eo_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.module == "EO"
    assert isinstance(cand.item.content, EOContent)


def test_synth_is_deterministic() -> None:
    clf = FakeCEFRClassifier()
    a = synthesize_eo_prompt(_input(seed=3), classifier=clf)
    b = synthesize_eo_prompt(_input(seed=3), classifier=clf)
    assert a.item.id == b.item.id
    assert a.item.model_dump() == b.item.model_dump()


def test_synth_task1_has_no_prep_time() -> None:
    cand = synthesize_eo_prompt(_input(task_number=1), classifier=FakeCEFRClassifier())
    assert cand.item.content.candidate_prep_time_s == 0  # type: ignore[union-attr]
    assert cand.item.content.target_duration_s == 180  # type: ignore[union-attr]


def test_synth_task2_has_prep_and_longer_duration() -> None:
    cand = synthesize_eo_prompt(_input(task_number=2), classifier=FakeCEFRClassifier())
    assert cand.item.content.candidate_prep_time_s == 60  # type: ignore[union-attr]
    assert cand.item.content.target_duration_s == 210  # type: ignore[union-attr]


def test_synth_task3_has_prep_and_longer_duration() -> None:
    cand = synthesize_eo_prompt(_input(task_number=3), classifier=FakeCEFRClassifier())
    assert cand.item.content.candidate_prep_time_s == 60  # type: ignore[union-attr]
    assert cand.item.content.target_duration_s == 210  # type: ignore[union-attr]


def test_synth_emits_non_empty_examiner_prompts() -> None:
    cand = synthesize_eo_prompt(_input(), classifier=FakeCEFRClassifier())
    prompts = cand.item.content.examiner_prompts  # type: ignore[union-attr]
    assert len(prompts) >= 1
    assert all(isinstance(p, str) and p.strip() for p in prompts)


def test_synth_rubric_version_pinned() -> None:
    cand = synthesize_eo_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.content.rubric_version == RUBRIC_VERSION == "eo.v1"  # type: ignore[union-attr]


def test_synth_provenance_uses_foundation_source() -> None:
    cand = synthesize_eo_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.provenance.source == SOURCE_NAME
    assert cand.item.provenance.license == SOURCE_LICENSE
    assert cand.item.provenance.synthesizer_version == SYNTHESIZER_VERSION


def test_synth_carries_placeholder_calibration_anchors() -> None:
    cand = synthesize_eo_prompt(_input(), classifier=FakeCEFRClassifier())
    anchors = cand.item.metadata.calibration_anchors
    assert anchors is not None
    assert set(anchors.keys()) == {"nclc_7", "nclc_9", "nclc_11"}


def test_synth_marks_synthetic_true() -> None:
    cand = synthesize_eo_prompt(_input(), classifier=FakeCEFRClassifier())
    assert cand.item.synthetic is True


def test_synth_uses_cefr_target_for_level() -> None:
    cand = synthesize_eo_prompt(
        EOSynthesisInput(task_number=3, cefr_target="C1"),
        classifier=FakeCEFRClassifier(),
    )
    assert cand.item.cefr_level == "C1"


def test_synth_records_cefr_confidence_from_classifier() -> None:
    cand = synthesize_eo_prompt(_input(), classifier=FakeCEFRClassifier())
    md = cand.item.metadata
    assert md.cefr_confidence is not None
    assert 0.0 <= md.cefr_confidence <= 1.0
    assert md.cefr_distribution is not None


def test_synth_invalid_task_number_raises() -> None:
    with pytest.raises(ValueError, match="task_number"):
        synthesize_eo_prompt(
            EOSynthesisInput(task_number=4, cefr_target="B2"),  # type: ignore[arg-type]
            classifier=FakeCEFRClassifier(),
        )


def test_synth_tags_task_number_in_metadata() -> None:
    cand = synthesize_eo_prompt(_input(task_number=2), classifier=FakeCEFRClassifier())
    assert "eo_task_2" in cand.item.metadata.tags
    assert "foundation_synth" in cand.item.metadata.tags
