"""EE drill tests (Phase 5 step 8).

Covers the word-count gate, the three EE drills (task, rewrite,
register-adjust), and their `Interaction` shape under the
rubric-pending posture.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from tcf_accel.schemas.common import Provenance
from tcf_accel.schemas.content import EEContent
from tcf_accel.schemas.item import Item
from tcf_accel_sla.drills import EERegisterAdjustDrill, EERewriteDrill, EETaskDrill, get_drill
from tcf_accel_sla.drills._ee_common import (
    WORD_COUNT_PENALTY_CAP,
    WORD_COUNT_TARGETS,
    count_words,
    in_word_band,
    word_count_penalty,
)


def _ee_item(task: int = 2) -> Item:
    return Item(
        id=uuid4(),
        module="EE",
        cefr_level="B2",
        difficulty_irt=7.0,
        discrimination_irt=1.0,
        content=EEContent(
            task_number=task,  # type: ignore[arg-type]
            prompt="Donnez votre opinion sur le télétravail.",
            target_word_count_range=(96, 132),
            required_canadian_context=(task != 1),
            rubric_version="ee.v1",
        ),
        provenance=Provenance(
            source="test",
            source_id="t",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
    )


def _words(n: int) -> str:
    """A space-separated string of `n` placeholder words."""
    return " ".join(f"w{i}" for i in range(n))


# ─── word-count gate ───────────────────────────────────────────


def test_targets_match_fei() -> None:
    # FEI canonical: 60 / 120 / 180.
    assert WORD_COUNT_TARGETS == {1: 60, 2: 120, 3: 180}


def test_count_words_whitespace_split() -> None:
    assert count_words("Bonjour, c'est moi.") == 3
    assert count_words("") == 0


def test_penalty_inside_band_is_zero() -> None:
    assert word_count_penalty(60, 60) == 0  # exact
    assert word_count_penalty(48, 60) == 0  # 80% boundary
    assert word_count_penalty(66, 60) == 0  # 110% boundary
    assert word_count_penalty(54, 60) == 0  # mid-band


def test_penalty_one_step_below_band() -> None:
    # 60 * 0.75 = 45 → exactly 5% out → -1
    assert word_count_penalty(45, 60) == -1


def test_penalty_two_steps_below_band() -> None:
    # 60 * 0.70 = 42 → 10% out → -2
    assert word_count_penalty(42, 60) == -2


def test_penalty_above_band() -> None:
    assert word_count_penalty(72, 60) == -2  # 120% → 10% over → 2 steps
    assert word_count_penalty(75, 60) == -3  # 125% → 15% over → 3 steps


def test_penalty_caps_at_negative_four() -> None:
    # Ratio = 50% → 30% below 80% → 6 steps → capped at -4.
    assert word_count_penalty(30, 60) == WORD_COUNT_PENALTY_CAP
    # Ratio = 200% → 90% above 110% → 18 steps → capped at -4.
    assert word_count_penalty(120, 60) == WORD_COUNT_PENALTY_CAP


def test_penalty_handles_zero_target() -> None:
    # Defensive: a malformed item with target=0 must not divide-by-zero.
    assert word_count_penalty(100, 0) == 0


def test_in_word_band_helper() -> None:
    assert in_word_band(60, 60) is True
    assert in_word_band(40, 60) is False


# ─── ee_task: core 3-task timed write ──────────────────────────


def test_ee_task_present_carries_word_range_and_budget() -> None:
    drill = EETaskDrill()
    step = drill.present(_ee_item(task=2))
    assert step.drill_kind == "ee_task"
    assert step.payload["task_number"] == 2
    assert step.payload["target_word_count_low"] == 96
    assert step.payload["target_word_count_high"] == 132
    # Task 2 = 20 min = 1_200_000 ms.
    assert step.expected_rt_ms == 1_200_000


def test_ee_task_grade_emits_rubric_pending() -> None:
    drill = EETaskDrill()
    item = _ee_item(task=2)
    text = _words(120)  # exact target
    result = drill.grade(item, {"text": text})
    # Rubric is Phase 7 — correctness is pending.
    assert result.correct is None
    assert result.partial_credit is None
    assert result.graded_score is not None
    gs = result.graded_score
    assert gs["pending"] is True
    assert gs["task_number"] == 2
    assert gs["word_count"] == 120
    assert gs["word_count_target"] == 120
    assert gs["word_count_penalty"] == 0
    assert gs["in_word_band"] is True
    assert gs["rubric_version"] == "ee.v1"


def test_ee_task_grade_records_out_of_band_penalty() -> None:
    drill = EETaskDrill()
    item = _ee_item(task=2)
    text = _words(60)  # 50% of target → cap
    result = drill.grade(item, {"text": text})
    assert result.graded_score is not None
    assert result.graded_score["in_word_band"] is False
    assert result.graded_score["word_count_penalty"] == WORD_COUNT_PENALTY_CAP


def test_ee_task_grade_empty_text() -> None:
    drill = EETaskDrill()
    item = _ee_item(task=2)
    result = drill.grade(item, {"text": ""})
    assert result.graded_score is not None
    assert result.graded_score["word_count"] == 0
    assert result.graded_score["word_count_penalty"] == WORD_COUNT_PENALTY_CAP


def test_ee_task_to_interaction_carries_drill_kind_and_pending() -> None:
    drill = EETaskDrill()
    item = _ee_item(task=2)
    result = drill.grade(item, {"text": _words(120)})
    interaction = drill.to_interaction(
        user_id=uuid4(),
        session_id=uuid4(),
        item=item,
        result=result,
        rt_ms=600_000,
        rating=3,
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    assert interaction.module == "EE"
    assert interaction.drill_kind == "ee_task"
    assert interaction.correct is None  # pending
    assert interaction.graded_score is not None
    assert interaction.graded_score["pending"] is True
    assert interaction.pronunciation is None
    assert interaction.audio_path is None


def test_ee_task_three_tasks_have_distinct_targets() -> None:
    drill = EETaskDrill()
    for task in (1, 2, 3):
        item = _ee_item(task=task)
        # Use an item with the correct word range for this task.
        if task == 1:
            item.content = EEContent(  # type: ignore[assignment]
                task_number=1,
                prompt="...",
                target_word_count_range=(48, 66),
                required_canadian_context=False,
                rubric_version="ee.v1",
            )
        elif task == 3:
            item.content = EEContent(  # type: ignore[assignment]
                task_number=3,
                prompt="...",
                target_word_count_range=(144, 198),
                required_canadian_context=True,
                rubric_version="ee.v1",
            )
        result = drill.grade(item, {"text": _words(WORD_COUNT_TARGETS[task])})
        assert result.graded_score is not None
        assert result.graded_score["word_count_target"] == WORD_COUNT_TARGETS[task]
        assert result.graded_score["in_word_band"] is True


# ─── ee_rewrite + ee_register_adjust ───────────────────────────


def test_ee_rewrite_emits_rubric_pending_with_word_count() -> None:
    drill = EERewriteDrill()
    item = _ee_item()
    result = drill.grade(item, {"text": "Voici une réécriture plus soutenue."})
    assert result.correct is None
    assert result.graded_score is not None
    assert result.graded_score["drill_origin"] == "ee_rewrite"
    assert result.graded_score["word_count"] == 5
    assert result.graded_score["pending"] is True


def test_ee_register_adjust_emits_rubric_pending() -> None:
    drill = EERegisterAdjustDrill()
    item = _ee_item()
    result = drill.grade(item, {"text": "Une formulation soignée."})
    assert result.correct is None
    assert result.graded_score is not None
    assert result.graded_score["drill_origin"] == "ee_register_adjust"
    assert result.graded_score["pending"] is True


def test_rubric_pending_flag_is_set_on_all_ee_drills() -> None:
    for kind in ("ee_task", "ee_rewrite", "ee_register_adjust"):
        assert get_drill(kind).spec.rubric_pending is True


# ─── registry ──────────────────────────────────────────────────


def test_registry_resolves_each_ee_kind() -> None:
    for kind in ("ee_task", "ee_rewrite", "ee_register_adjust"):
        drill = get_drill(kind)
        assert drill.spec.drill_kind == kind
        assert drill.spec.module == "EE"


def test_registry_maps_legacy_writing_drill_types_to_ee_task() -> None:
    from tcf_accel_sla.drills import resolve_drill_kind  # noqa: PLC0415

    assert resolve_drill_kind("EE", "writing_short") == "ee_task"
    assert resolve_drill_kind("EE", "writing_long") == "ee_task"
    # Phase 5 new DrillType names fall through to themselves.
    assert resolve_drill_kind("EE", "ee_rewrite") == "ee_rewrite"
    assert resolve_drill_kind("EE", "ee_register_adjust") == "ee_register_adjust"


# ─── perfect-agent style: full session shape ───────────────────


def test_perfect_agent_ee_task_session_emits_pending_interactions() -> None:
    """A learner who submits the target word count produces well-typed
    pending interactions; Phase 7 will fill in the rubric scores."""
    drill = EETaskDrill()
    user, session = uuid4(), uuid4()
    now = datetime(2026, 5, 28, tzinfo=UTC)
    for task, words in [(1, 60), (2, 120), (3, 180)]:
        ranges = {1: (48, 66), 2: (96, 132), 3: (144, 198)}[task]
        item = _ee_item(task=task)
        item.content = EEContent(  # type: ignore[assignment]
            task_number=task,  # type: ignore[arg-type]
            prompt="...",
            target_word_count_range=ranges,
            required_canadian_context=(task != 1),
            rubric_version="ee.v1",
        )
        result = drill.grade(item, {"text": _words(words)})
        interaction = drill.to_interaction(
            user_id=user,
            session_id=session,
            item=item,
            result=result,
            rt_ms=600_000,
            rating=3,
            created_at=now,
        )
        assert interaction.module == "EE"
        assert interaction.drill_kind == "ee_task"
        assert interaction.correct is None
        assert interaction.graded_score is not None
        assert interaction.graded_score["in_word_band"] is True


def test_perfect_agent_step_back_off_band_records_penalty() -> None:
    drill = EETaskDrill()
    item = _ee_item(task=2)
    # 60 of 120 target → 50% → -4 cap.
    result = drill.grade(item, {"text": _words(60)})
    assert result.graded_score is not None
    assert result.graded_score["word_count_penalty"] == WORD_COUNT_PENALTY_CAP
