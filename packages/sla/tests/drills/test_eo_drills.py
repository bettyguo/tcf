"""EO drill + audio-pipeline + follow-up tests (Phase 5 step 9).

Uses the `TCF_ACCEL_{ASR,MFA}_BACKEND=stub` env vars so the audio
pipeline is deterministic and dependency-free. The drills are graded
end-to-end with stub-generated audio, producing typed
`PronunciationSignal`s on each `Interaction`.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from tcf_accel.schemas.common import Provenance
from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item
from tcf_accel.schemas.pronunciation import PronunciationSignal
from tcf_accel_sla.audio import AudioPipelineOutputs, run_audio_pipeline
from tcf_accel_sla.drills import (
    EOPictureDrill,
    EORepairDrill,
    EORoleplayDrill,
    EOSpontaneousDrill,
    EOTaskDrill,
    EOTextAltDrill,
    get_drill,
    resolve_drill_kind,
)
from tcf_accel_sla.drills._eo_followup import (
    follow_up_pool_size,
    sample_follow_ups,
)

# ─── env-var fixture: stub backends for the whole module ──────


@pytest.fixture(autouse=True)
def _stub_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")


# ─── helpers ───────────────────────────────────────────────────


def _eo_item(task: int = 1) -> Item:
    duration = {1: 180, 2: 210, 3: 210}[task]
    prep = {1: 0, 2: 120, 3: 0}[task]
    return Item(
        id=uuid4(),
        module="EO",
        cefr_level="B2",
        difficulty_irt=7.0,
        discrimination_irt=1.0,
        content=EOContent(
            task_number=task,  # type: ignore[arg-type]
            examiner_prompts=["Présentez-vous.", "Parlez de votre travail."],
            candidate_prep_time_s=prep,
            target_duration_s=duration,
            rubric_version="eo.v1",
        ),
        provenance=Provenance(
            source="test",
            source_id="t",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
    )


def _good_audio() -> bytes:
    # 10 s of PCM16 mono @16k — long enough to clear the
    # insufficient-data gate (≥ 2 s + ≥ 8 phonemes); not 0x00-prefixed
    # so the stub backends report high confidence.
    return b"\xff\xff" * (10 * 16_000)


# ─── run_audio_pipeline ────────────────────────────────────────


def test_pipeline_returns_typed_outputs_with_signal() -> None:
    outputs = run_audio_pipeline(_good_audio(), sample_rate_hz=16_000)
    assert isinstance(outputs, AudioPipelineOutputs)
    assert isinstance(outputs.signal, PronunciationSignal)
    assert outputs.signal.signal_kind == "coarse_proxy"
    # Stub ASR transcript is the fixed three-word French sentence.
    assert outputs.asr.transcript == "bonjour le monde"


def test_pipeline_short_audio_routes_to_insufficient_data() -> None:
    short = b"\xff\xff" * 1000  # ~62 ms
    outputs = run_audio_pipeline(short, sample_rate_hz=16_000)
    # Stub ASR reports duration ~ 0.06 s < INSUFFICIENT_DURATION_S → gate fires.
    assert outputs.signal.display_label == "insufficient_data"


# ─── EO core: eo_task ──────────────────────────────────────────


def test_eo_task_present_carries_task_metadata_and_followups() -> None:
    drill = EOTaskDrill()
    step = drill.present(_eo_item(task=1))
    assert step.drill_kind == "eo_task"
    assert step.payload["task_number"] == 1
    assert step.payload["candidate_prep_time_s"] == 0
    assert step.payload["target_duration_s"] == 180
    # Task 1 → follow-ups are pulled from the stub pool.
    follow_ups = step.payload["follow_up_prompts"]
    assert isinstance(follow_ups, list)
    assert len(follow_ups) == 2
    assert all(isinstance(s, str) and s for s in follow_ups)


def test_eo_task_grade_runs_pipeline_and_emits_signal() -> None:
    drill = EOTaskDrill()
    item = _eo_item()
    result = drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    # Rubric is Phase 7-pending.
    assert result.correct is None
    assert result.pronunciation is not None
    assert result.pronunciation.signal_kind == "coarse_proxy"
    assert result.graded_score is not None
    gs = result.graded_score
    assert gs["pending"] is True
    assert gs["drill_origin"] == "eo_task"
    assert gs["task_number"] == 1
    assert gs["pronunciation_display_label"] in {"weak", "fair", "strong", "insufficient_data"}


def test_eo_task_grade_no_audio_returns_no_audio_marker() -> None:
    drill = EOTaskDrill()
    item = _eo_item()
    result = drill.grade(item, {})  # no audio key
    assert result.correct is False
    assert result.pronunciation is None
    assert result.graded_score is not None
    assert result.graded_score["phase7_status"] == "no_audio"
    assert result.graded_score["pending"] is False


def test_eo_task_to_interaction_attaches_pronunciation_and_no_audio_path() -> None:
    drill = EOTaskDrill()
    item = _eo_item()
    result = drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    interaction = drill.to_interaction(
        user_id=uuid4(),
        session_id=uuid4(),
        item=item,
        result=result,
        rt_ms=120_000,
        rating=3,
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    assert interaction.module == "EO"
    assert interaction.drill_kind == "eo_task"
    assert interaction.pronunciation is not None
    # ADR-017: default is no on-disk audio retention.
    assert interaction.audio_path is None
    # raw_response carries the byte *count*, not the audio bytes.
    assert "audio_bytes" in interaction.raw_response
    assert interaction.raw_response["audio_bytes"] > 0


# ─── EO supplementary drills (picture / spontaneous / role-play) ─


@pytest.mark.parametrize(
    ("drill_cls", "kind", "expected_total_s"),
    [
        (EOPictureDrill, "eo_picture", 30 + 90),
        (EOSpontaneousDrill, "eo_spontaneous", 5 + 60),
        (EORoleplayDrill, "eo_roleplay", 90),
    ],
)
def test_supplementary_drill_timings_and_grade_shape(
    drill_cls: type,
    kind: str,
    expected_total_s: int,
) -> None:
    drill = drill_cls()
    item = _eo_item()
    step = drill.present(item)
    assert step.drill_kind == kind
    assert step.expected_rt_ms == expected_total_s * 1000
    result = drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    assert result.pronunciation is not None
    assert result.graded_score is not None
    assert result.graded_score["drill_origin"] == kind


# ─── EO repair (round-robin stub) ─────────────────────────────


def test_eo_repair_picks_a_sub_criterion() -> None:
    drill = EORepairDrill()
    item = _eo_item()
    step = drill.present(item)
    pick = step.payload["target_sub_criterion"]
    assert pick in {
        "task_completion",
        "fluency_pace",
        "pronunciation_prosody",
        "lexical_range",
        "grammatical_accuracy",
        "interaction_responsiveness",
    }


def test_eo_repair_pick_is_deterministic_per_item() -> None:
    # Same item → same sub-criterion (the round-robin uses the UUID as a seed).
    item = _eo_item()
    drill = EORepairDrill()
    a = drill.present(item).payload["target_sub_criterion"]
    b = drill.present(item).payload["target_sub_criterion"]
    assert a == b


def test_eo_repair_grade_propagates_sub_criterion_into_graded_score() -> None:
    drill = EORepairDrill()
    item = _eo_item()
    step = drill.present(item)
    result = drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    assert result.graded_score is not None
    assert result.graded_score["target_sub_criterion"] == step.payload["target_sub_criterion"]


# ─── EO text-alt (ADR-029 symmetric) ──────────────────────────


def test_eo_text_alt_declares_module_ee() -> None:
    # The load-bearing accessibility invariant: the EO text alternative
    # emits `module=EE`, never EO, so the EO posterior stays
    # calibrated against actual recordings (symmetric to ADR-029).
    assert EOTextAltDrill().spec.module == "EE"
    assert EOTextAltDrill().spec.drill_kind == "eo_text_alt"


def test_eo_text_alt_grade_emits_pending_rubric_with_drill_origin() -> None:
    drill = EOTextAltDrill()
    item = _eo_item()
    result = drill.grade(item, {"text": "Bonjour, je voudrais aborder ce sujet."})
    assert result.correct is None
    assert result.graded_score is not None
    assert result.graded_score["drill_origin"] == "eo_text_alt"


def test_eo_text_alt_interaction_writes_module_ee() -> None:
    drill = EOTextAltDrill()
    item = _eo_item()
    result = drill.grade(item, {"text": "Une réponse écrite."})
    interaction = drill.to_interaction(
        user_id=uuid4(),
        session_id=uuid4(),
        item=item,
        result=result,
        rt_ms=60_000,
        rating=3,
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    # Module is EE (the load-bearing assertion). Even though the item
    # is an EOContent, the drill's spec.module wins, keeping the EO
    # posterior calibrated against real-audio drills only.
    assert interaction.module == "EE"
    assert interaction.drill_kind == "eo_text_alt"


# ─── Registry + DrillType mapping ──────────────────────────────


def test_registry_resolves_all_eo_drill_kinds() -> None:
    for kind, expected_module in [
        ("eo_task", "EO"),
        ("eo_picture", "EO"),
        ("eo_spontaneous", "EO"),
        ("eo_roleplay", "EO"),
        ("eo_repair", "EO"),
        ("eo_text_alt", "EE"),  # accessibility alt
    ]:
        drill = get_drill(kind)
        assert drill.spec.drill_kind == kind
        assert drill.spec.module == expected_module


def test_legacy_speaking_drill_types_map_to_eo_drills() -> None:
    assert resolve_drill_kind("EO", "speaking_mono") == "eo_task"
    assert resolve_drill_kind("EO", "speaking_role") == "eo_roleplay"
    # Phase 5 new DrillType names fall through.
    assert resolve_drill_kind("EO", "eo_picture") == "eo_picture"
    assert resolve_drill_kind("EO", "eo_spontaneous") == "eo_spontaneous"
    assert resolve_drill_kind("EO", "eo_repair") == "eo_repair"


# ─── EO follow-up stub (audit gate §14) ───────────────────────


def test_followup_pool_meets_audit_floor_per_task() -> None:
    # phase5_audit.md §14: the local stub pool size ≥ 8 per task that
    # has follow-ups (Tasks 1 and 3). Task 2 has none.
    assert follow_up_pool_size(1) >= 8
    assert follow_up_pool_size(3) >= 8
    assert follow_up_pool_size(2) == 0


def test_followup_returns_empty_for_task_without_pool() -> None:
    assert sample_follow_ups(task_number=2, seed_text="x", n=3) == []


def test_followup_picks_are_deterministic_per_seed() -> None:
    a = sample_follow_ups(task_number=1, seed_text="learner-said-X", n=2)
    b = sample_follow_ups(task_number=1, seed_text="learner-said-X", n=2)
    assert a == b


def test_followup_picks_change_with_seed() -> None:
    a = sample_follow_ups(task_number=1, seed_text="seed-A", n=2)
    b = sample_follow_ups(task_number=1, seed_text="seed-B-different", n=2)
    assert a != b


def test_followup_picks_are_unique_within_a_call() -> None:
    picks = sample_follow_ups(task_number=1, seed_text="x", n=5)
    assert len(picks) == len(set(picks))


# ─── Capability sanity: env-var contract ──────────────────────


def test_module_runs_under_stub_backends() -> None:
    # If this fixture-managed env-var setup ever broke, the rest of
    # the file would still pass (the pipeline would still try to run);
    # this test pins the env-var values explicitly.
    assert os.environ["TCF_ACCEL_ASR_BACKEND"] == "stub"
    assert os.environ["TCF_ACCEL_MFA_BACKEND"] == "stub"
