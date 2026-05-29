"""`LLMCriticStub` tests (Phase 7).

The stub is deterministic, never gives 5/5 (the strict-grading rule),
honors `force_scores=` for the inflation-guard tests, and respects
the EE / EO rubric dimension lists.
"""

from __future__ import annotations

from tcf_accel_ml.scoring.llm.critic import EE_RUBRIC_DIMENSIONS, EO_RUBRIC_DIMENSIONS
from tcf_accel_ml.scoring.llm.stub import LLMCriticStub


def test_stub_is_deterministic_for_ee() -> None:
    s = LLMCriticStub()
    a = s.critique_ee(
        prompt="x", text="Bonjour.", rubric_version="ee.v1",
        task_number=1, target_word_count_range=(60, 120),
        required_canadian_context=False,
    )
    b = s.critique_ee(
        prompt="x", text="Bonjour.", rubric_version="ee.v1",
        task_number=1, target_word_count_range=(60, 120),
        required_canadian_context=False,
    )
    assert a.rubric_scores == b.rubric_scores


def test_stub_returns_all_ee_dimensions() -> None:
    s = LLMCriticStub()
    out = s.critique_ee(
        prompt="x", text="Bonjour le monde",
        rubric_version="ee.v1", task_number=2,
        target_word_count_range=(120, 150),
        required_canadian_context=True,
    )
    assert set(out.rubric_scores) == set(EE_RUBRIC_DIMENSIONS)


def test_stub_returns_all_eo_dimensions() -> None:
    s = LLMCriticStub()
    out = s.critique_eo(
        prompt="x", transcript="Bonjour le monde",
        rubric_version="eo.v1", task_number=1, duration_s=10.0,
    )
    assert set(out.rubric_scores) == set(EO_RUBRIC_DIMENSIONS)


def test_stub_never_gives_five_without_evidence() -> None:
    # The stub's strict-grading promise: no 5/5 on any dimension.
    s = LLMCriticStub()
    out = s.critique_ee(
        prompt="x",
        text=("Le télétravail à Montréal est avantageux car il économise du "
              "temps. Cependant, il isole les employés. Par ailleurs, la "
              "Régie du logement encourage le télétravail. Donc, un "
              "équilibre est nécessaire."),
        rubric_version="ee.v1", task_number=2,
        target_word_count_range=(50, 200),
        required_canadian_context=True,
    )
    assert all(v < 5 for v in out.rubric_scores.values())


def test_stub_force_scores_override() -> None:
    forced = {dim: 5 for dim in EE_RUBRIC_DIMENSIONS}
    s = LLMCriticStub(force_scores=forced)
    out = s.critique_ee(
        prompt="x", text="anything",
        rubric_version="ee.v1", task_number=1,
        target_word_count_range=(60, 120),
        required_canadian_context=False,
    )
    assert all(v == 5 for v in out.rubric_scores.values())


def test_stub_emits_errors_from_heuristic_detector() -> None:
    s = LLMCriticStub()
    out = s.critique_ee(
        prompt="x",
        text="Si j'aurais le choix, j'irais à Montréal.",
        rubric_version="ee.v1", task_number=2,
        target_word_count_range=(60, 120),
        required_canadian_context=True,
    )
    assert any(e.error_type == "tense" for e in out.error_annotations)
