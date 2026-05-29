"""EO repair-after-feedback drill (`phase5_design.md §4.4`).

After a prior EO interaction, identify the lowest-scoring rubric
sub-criterion and run a targeted micro-drill on it (e.g. subjunctive
triggers, liaison patterns, discourse markers).

Phase 5 ships the **shell**: the drill records audio and pipes it
through the standard EO pipeline, tagging the result with which
sub-criterion the micro-drill addressed. The *identifier* (which
sub-criterion was lowest in the prior interaction) is the Phase 7
hand-off — Phase 5 round-robins across the six SpeakingRubric
sub-criteria so the audit (`phase5_audit.md §1` repair-coverage
entry) sees diverse selections.

The round-robin uses the item's id as a deterministic seed, so the
same prior interaction always routes to the same sub-criterion until
Phase 7 plugs in the real selector.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._eo_common import grade_eo_recording
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

# The six SpeakingRubric sub-criteria (cf. `tcf_accel.schemas.scoring.
# SpeakingRubric`). Phase 7 replaces the round-robin with a real
# "which one was lowest" lookup over the prior interaction.
_SUB_CRITERIA: Final[tuple[str, ...]] = (
    "task_completion",
    "fluency_pace",
    "pronunciation_prosody",
    "lexical_range",
    "grammatical_accuracy",
    "interaction_responsiveness",
)


def _round_robin_pick(item_id_str: str) -> str:
    """Deterministic sub-criterion pick (Phase 5 stub)."""
    # `hash()` would be salted between processes; use the int form of
    # the UUID to get a stable seed across runs.
    return _SUB_CRITERIA[int(item_id_str.replace("-", ""), 16) % len(_SUB_CRITERIA)]


class EORepairDrill(Drill):
    """Repair-after-feedback drill. Phase 5 stub identifier; Phase 7 scores."""

    spec = DrillSpec(
        drill_kind="eo_repair",
        module="EO",
        requires_audio_in=True,
        rubric_pending=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the prompt + the targeted sub-criterion (stub-selected)."""
        content = item.content
        assert isinstance(content, EOContent)
        sub_criterion = _round_robin_pick(str(item.id))
        return DrillStep(
            item_id=item.id,
            drill_kind="eo_repair",
            payload={
                "examiner_prompts": list(content.examiner_prompts),
                "target_duration_s": content.target_duration_s,
                "rubric_version": content.rubric_version,
                "target_sub_criterion": sub_criterion,
                "phase7_status": "stub_identifier",  # Phase 7 swaps in real selector
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Grade the recording; carry the targeted sub-criterion through."""
        content = item.content
        assert isinstance(content, EOContent)
        result = grade_eo_recording(
            response,
            drill_kind="eo_repair",
            rubric_version=content.rubric_version,
        )
        # Annotate the graded_score with the sub-criterion this drill targeted.
        if result.graded_score is not None:
            updated = dict(result.graded_score)
            updated["target_sub_criterion"] = _round_robin_pick(str(item.id))
            # `frozen=True` on DrillResult → return a fresh instance.
            return DrillResult(
                correct=result.correct,
                partial_credit=result.partial_credit,
                raw_response=result.raw_response,
                pronunciation=result.pronunciation,
                graded_score=updated,
            )
        return result


__all__ = ["EORepairDrill"]
