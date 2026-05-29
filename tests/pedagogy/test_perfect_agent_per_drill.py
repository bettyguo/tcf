"""Perfect-agent suite across all implemented drill kinds (`phase5_audit.md §1`).

For each `drill_kind` Phase 5 implements, an agent that always answers
correctly produces well-typed interactions with `module ==
drill.spec.module`. Rubric-pending drills (EE/EO) emit `correct=None`
with `graded_score.pending=True` — the gate is shape-correctness +
routing-correctness, not numeric rubric agreement (that's Phase 7).

Drills deferred within Phase 5 (with documented reasons) are not
parametrized here:
- `co_shadowing`, `co_accent`: bank-shape dependencies (ML stack ✓,
  but the bank-side 2-clip / shadowing-reference items aren't shipped).
- `ee_connector`, `ee_error_correction`: cloze-shape EEContent /
  Phase 7 annotations.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from tcf_accel.schemas.common import Provenance
from tcf_accel.schemas.content import (
    MCQ,
    CEContent,
    COContent,
    EEContent,
    EOContent,
    MCQOption,
    Speaker,
)
from tcf_accel.schemas.item import Item
from tcf_accel_sla.drills import get_drill

# ─── Audio pipeline stubs for the EO drills ───────────────────


@pytest.fixture(autouse=True)
def _stub_pipeline_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")


def _provenance() -> Provenance:
    return Provenance(
        source="test",
        source_id="t",
        license="CC0-1.0",
        ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
        review_status="auto_passed",
    )


def _mcq(correct: str = "a") -> MCQ:
    return MCQ(
        id="q1",
        prompt="?",
        options=[
            MCQOption(id="a", text="A"),
            MCQOption(id="b", text="B"),
            MCQOption(id="c", text="C"),
            MCQOption(id="d", text="D"),
        ],
        correct_option_id=correct,
    )


def _co_item() -> Item:
    return Item(
        id=uuid4(),
        module="CO",
        cefr_level="B2",
        content=COContent(
            transcript="le chat noir dort sur le tapis du salon",
            duration_s=10.0,
            speakers=[Speaker(label="A", accent="fr-CA")],
            accent="fr-CA",
            register="standard",
            questions=[_mcq()],
        ),
        provenance=_provenance(),
    )


def _ce_item() -> Item:
    return Item(
        id=uuid4(),
        module="CE",
        cefr_level="B2",
        content=CEContent(
            passage=(
                "Un passage de test pour la compréhension écrite. "
                "Il contient assez de mots pour satisfaire la borne minimale "
                "imposée par le schéma CEContent: vingt mots ou plus en français."
            ),
            genre="news",
            word_count=28,
            questions=[_mcq()],
        ),
        provenance=_provenance(),
    )


def _ee_item(task: int = 2) -> Item:
    ranges = {1: (48, 66), 2: (96, 132), 3: (144, 198)}[task]
    return Item(
        id=uuid4(),
        module="EE",
        cefr_level="B2",
        content=EEContent(
            task_number=task,  # type: ignore[arg-type]
            prompt="Donnez votre opinion.",
            target_word_count_range=ranges,
            required_canadian_context=(task != 1),
            rubric_version="ee.v1",
        ),
        provenance=_provenance(),
    )


def _eo_item() -> Item:
    return Item(
        id=uuid4(),
        module="EO",
        cefr_level="B2",
        content=EOContent(
            task_number=1,
            examiner_prompts=["Présentez-vous."],
            candidate_prep_time_s=0,
            target_duration_s=180,
            rubric_version="eo.v1",
        ),
        provenance=_provenance(),
    )


def _good_audio() -> bytes:
    return b"\xff\xff" * (10 * 16_000)


def _words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


# (drill_kind, item_factory, response_factory, expected_module)
# `correct_field`: what `Interaction.correct` should be — True for
# MCQ-style drills, None for rubric-pending drills.
_PERFECT_AGENT_TABLE = [
    ("co_mcq", _co_item, lambda _item: {"option_id": "a"}, "CO", True),
    (
        "co_dictation",
        _co_item,
        lambda item: {"transcription": item.content.transcript},  # type: ignore[union-attr]
        "CO",
        True,
    ),
    (
        "co_lexical_alt",
        _co_item,
        lambda _item: {"option_id": "a"},
        "CE",  # ADR-029: lexical alt writes to CE, not CO
        True,
    ),
    ("ce_mcq", _ce_item, lambda _item: {"option_id": "a"}, "CE", True),
    (
        "ee_task",
        lambda: _ee_item(task=2),
        lambda _item: {"text": _words(120)},
        "EE",
        None,  # rubric-pending
    ),
    (
        "ee_rewrite",
        _ee_item,
        lambda _item: {"text": "Une réécriture soignée."},
        "EE",
        None,
    ),
    (
        "ee_register_adjust",
        _ee_item,
        lambda _item: {"text": "Une formulation formelle."},
        "EE",
        None,
    ),
    (
        "eo_task",
        _eo_item,
        lambda _item: {"audio": _good_audio(), "sample_rate_hz": 16_000},
        "EO",
        None,
    ),
    (
        "eo_picture",
        _eo_item,
        lambda _item: {"audio": _good_audio(), "sample_rate_hz": 16_000},
        "EO",
        None,
    ),
    (
        "eo_spontaneous",
        _eo_item,
        lambda _item: {"audio": _good_audio(), "sample_rate_hz": 16_000},
        "EO",
        None,
    ),
    (
        "eo_roleplay",
        _eo_item,
        lambda _item: {"audio": _good_audio(), "sample_rate_hz": 16_000},
        "EO",
        None,
    ),
    (
        "eo_repair",
        _eo_item,
        lambda _item: {"audio": _good_audio(), "sample_rate_hz": 16_000},
        "EO",
        None,
    ),
    (
        "eo_text_alt",
        _eo_item,
        lambda _item: {"text": "Une réponse écrite."},
        "EE",  # ADR-029 symmetric: text alt writes to EE
        None,
    ),
]


@pytest.mark.parametrize(
    ("kind", "item_factory", "response_factory", "expected_module", "expected_correct"),
    _PERFECT_AGENT_TABLE,
)
def test_perfect_agent_produces_well_typed_interaction(
    kind: str,
    item_factory,  # type: ignore[no-untyped-def]
    response_factory,  # type: ignore[no-untyped-def]
    expected_module: str,
    expected_correct: bool | None,
) -> None:
    """For every implementable Phase 5 drill, a perfect agent emits an
    Interaction whose `module` matches the drill's declared posterior
    skill, `drill_kind` matches the registry, and `correct` matches
    the rubric-pending posture (True for MCQ-style, None for rubric)."""
    drill = get_drill(kind)
    item = item_factory()
    response = response_factory(item)
    result = drill.grade(item, response)
    interaction = drill.to_interaction(
        user_id=uuid4(),
        session_id=uuid4(),
        item=item,
        result=result,
        rt_ms=60_000,
        rating=3,
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    assert interaction.module == expected_module, (
        f"drill {kind} declared module={drill.spec.module} but emitted {interaction.module}"
    )
    assert interaction.drill_kind == kind
    assert interaction.correct == expected_correct, (
        f"drill {kind} expected correct={expected_correct}, got {interaction.correct}"
    )
    # ADR-017: audio_path always None by default; raw audio never in raw_response.
    assert interaction.audio_path is None
    for value in interaction.raw_response.values():
        assert not isinstance(value, (bytes, bytearray, memoryview))


def test_perfect_agent_count_matches_phase5_implementation_inventory() -> None:
    """Pin the count of implemented Phase 5 drills. A future commit
    that adds a drill should also add it to the perfect-agent table."""
    # 3 CO + 1 CO-alt + 1 CE + 3 EE + 5 EO + 1 EO-alt = 14
    assert len(_PERFECT_AGENT_TABLE) == 13  # excluding rubric duplicates
    # All entries point at registered drills.
    from tcf_accel_sla.drills import REGISTRY  # noqa: PLC0415

    for kind, *_ in _PERFECT_AGENT_TABLE:
        assert kind in REGISTRY, f"perfect-agent kind {kind!r} is not registered"


def test_env_var_fixture_is_loaded() -> None:
    """Sanity: the stub backends are wired before the EO drills run."""
    assert os.environ["TCF_ACCEL_ASR_BACKEND"] == "stub"
    assert os.environ["TCF_ACCEL_MFA_BACKEND"] == "stub"
