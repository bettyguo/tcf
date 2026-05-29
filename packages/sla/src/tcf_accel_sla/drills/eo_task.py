"""EO core drill — 3-task recorded (`phase5_design.md §4.4`).

Task 1 (~3 min) — examiner Q&A.
Task 2 (~3.5 min) — describe + compare two images / scenarios. 2 min prep.
Task 3 (~3.5 min) — argue a position then respond to objections.

Phase 5 ships the pipeline: record → ASR → MFA → prosody →
`PronunciationSignal`. Phase 7 plugs in the rubric scorer via the
`score_eo` worker's hand-off registry. The follow-up prompts for Task 1
and Task 3 come from `_eo_followup.py` (local stub pool until the
operator opts into the LiteLLM gateway).
"""

from __future__ import annotations

from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._eo_common import grade_eo_recording
from tcf_accel_sla.drills._eo_followup import sample_follow_ups
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

# Per-task total time budgets in ms (prep + production). FEI §1.1.
_TASK_TIME_MS: dict[int, int] = {1: 180_000, 2: 210_000, 3: 210_000}


class EOTaskDrill(Drill):
    """Core 3-task EO recorded drill. Phase 7 scores the rubric."""

    spec = DrillSpec(
        drill_kind="eo_task",
        module="EO",
        requires_audio_in=True,
        requires_audio_out=True,  # examiner TTS prompts
        rubric_pending=True,
        accessibility_alt="eo_text_alt",
    )

    def present(self, item: Item) -> DrillStep:
        """Render the examiner prompts + prep/duration + follow-up seed."""
        content = item.content
        assert isinstance(content, EOContent)
        follow_ups = sample_follow_ups(
            task_number=content.task_number,
            seed_text=" ".join(content.examiner_prompts),
            n=2,
        )
        return DrillStep(
            item_id=item.id,
            drill_kind="eo_task",
            single_play=False,
            expected_rt_ms=_TASK_TIME_MS.get(content.task_number, 210_000),
            payload={
                "task_number": content.task_number,
                "examiner_prompts": list(content.examiner_prompts),
                "candidate_prep_time_s": content.candidate_prep_time_s,
                "target_duration_s": content.target_duration_s,
                "rubric_version": content.rubric_version,
                "follow_up_prompts": follow_ups,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Run the audio pipeline; emit a rubric-pending result."""
        content = item.content
        assert isinstance(content, EOContent)
        return grade_eo_recording(
            response,
            drill_kind="eo_task",
            rubric_version=content.rubric_version,
            task_number=content.task_number,
        )


__all__ = ["EOTaskDrill"]
