"""Unit + perfect-agent tests for the CO/CE core MCQ drills.

The perfect-agent test (`phase5_audit.md §1`) is the structural
correctness gate: an agent that always picks the correct option must
produce 100%-correct interactions, each well-typed and carrying the
drill's declared module.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from tcf_accel.schemas.common import Provenance
from tcf_accel.schemas.content import MCQ, CEContent, COContent, MCQOption, Speaker
from tcf_accel.schemas.item import Item
from tcf_accel_sla.drills import CEMCQDrill, COMCQDrill, get_drill
from tcf_accel_sla.drills.base import grade_mcq


def _mcq(correct: str = "a") -> MCQ:
    return MCQ(
        id="q1",
        prompt="Qui parle ?",
        options=[
            MCQOption(id="a", text="Annick"),
            MCQOption(id="b", text="Pierre"),
            MCQOption(id="c", text="Marie"),
            MCQOption(id="d", text="Luc"),
        ],
        correct_option_id=correct,
    )


def _prov() -> Provenance:
    return Provenance(
        source="hand_authored",
        source_id="t",
        license="CC-BY-SA-4.0",
        ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
        review_status="auto_passed",
    )


def _co_item() -> Item:
    return Item(
        id=uuid4(),
        module="CO",
        cefr_level="B1",
        content=COContent(
            transcript="Bonjour, c'est Annick.",
            duration_s=8.5,
            speakers=[Speaker(label="A", accent="fr-CA")],
            accent="fr-CA",
            register="standard",
            questions=[_mcq()],
        ),
        provenance=_prov(),
    )


def _ce_item() -> Item:
    return Item(
        id=uuid4(),
        module="CE",
        cefr_level="B2",
        content=CEContent(
            passage="Avis aux clients : nous serons fermés lundi en raison de travaux.",
            genre="admin",
            word_count=21,
            questions=[_mcq()],
        ),
        provenance=_prov(),
    )


# ─── grade_mcq ─────────────────────────────────────────────────


def test_grade_mcq_option_id_and_answer_keys() -> None:
    q = _mcq("a")
    assert grade_mcq(q, {"option_id": "a"}) is True
    assert grade_mcq(q, {"answer": "a"}) is True
    assert grade_mcq(q, {"option_id": "b"}) is False
    assert grade_mcq(q, {}) is False  # timeout / no answer is wrong, not an error


# ─── CO single-play contract ───────────────────────────────────


def test_co_drill_step_is_single_play() -> None:
    step = COMCQDrill().present(_co_item())
    assert step.single_play is True
    assert step.drill_kind == "co_mcq"
    # Transcript must NOT be in the present payload (ADR-029: withheld pre-answer).
    assert "transcript" not in step.payload


def test_co_drill_budget_is_audio_plus_window() -> None:
    item = _co_item()
    step = COMCQDrill().present(item)
    # 8.5 s audio + 20 s window = 28.5 s → 28500 ms.
    assert step.expected_rt_ms == 28500


def test_co_drill_module_is_co() -> None:
    assert COMCQDrill().spec.module == "CO"


def test_co_drill_records_replay_count() -> None:
    item = _co_item()
    result = COMCQDrill().grade(item, {"option_id": "a", "audio_replays": 0})
    assert result.correct is True
    assert result.raw_response["audio_replays"] == 0


# ─── CE drill ──────────────────────────────────────────────────


def test_ce_drill_not_single_play() -> None:
    step = CEMCQDrill().present(_ce_item())
    assert step.single_play is False
    assert step.payload["genre"] == "admin"


def test_ce_drill_module_is_ce() -> None:
    assert CEMCQDrill().spec.module == "CE"


# ─── registry ──────────────────────────────────────────────────


def test_registry_resolves_implemented_kinds() -> None:
    assert get_drill("co_mcq").spec.drill_kind == "co_mcq"
    assert get_drill("ce_mcq").spec.drill_kind == "ce_mcq"


def test_registry_raises_for_unimplemented_kind() -> None:
    # `ee_connector` is in the DrillKind enum but its implementation
    # depends on cloze-shaped EE items the synthetic bank doesn't
    # carry (deferred to the real-bank work; see phase5_design.md §17).
    with pytest.raises(NotImplementedError, match="ee_connector"):
        get_drill("ee_connector")


# ─── perfect-agent (phase5_audit.md §1) ────────────────────────


def test_perfect_agent_co_mcq_100pct() -> None:
    drill = COMCQDrill()
    user, session = uuid4(), uuid4()
    now = datetime(2026, 5, 28, tzinfo=UTC)
    seen = correct = 0
    for _ in range(10):
        item = _co_item()
        question = item.content.questions[0]  # type: ignore[union-attr]
        # The "perfect agent" always selects the correct option.
        result = drill.grade(item, {"option_id": question.correct_option_id})
        interaction = drill.to_interaction(
            user_id=user,
            session_id=session,
            item=item,
            result=result,
            rt_ms=12000,
            rating=3,
            created_at=now,
        )
        seen += 1
        correct += int(bool(interaction.correct))
        # Every interaction is well-typed and carries the drill's module.
        assert interaction.module == "CO"
        assert interaction.drill_kind == "co_mcq"
        assert interaction.pronunciation is None
        assert interaction.audio_path is None
    assert seen == 10
    assert correct == 10  # 100% accuracy


def test_perfect_agent_ce_mcq_100pct() -> None:
    drill = CEMCQDrill()
    user, session = uuid4(), uuid4()
    now = datetime(2026, 5, 28, tzinfo=UTC)
    correct = 0
    for _ in range(10):
        item = _ce_item()
        question = item.content.questions[0]  # type: ignore[union-attr]
        result = drill.grade(item, {"option_id": question.correct_option_id})
        interaction = drill.to_interaction(
            user_id=user,
            session_id=session,
            item=item,
            result=result,
            rt_ms=30000,
            rating=3,
            created_at=now,
        )
        correct += int(bool(interaction.correct))
        assert interaction.module == "CE"
        assert interaction.drill_kind == "ce_mcq"
    assert correct == 10
