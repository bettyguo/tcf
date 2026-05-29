"""EO supplementary drill — role-play (`phase5_design.md §4.4`).

A 90-second interactive role-play; e.g. "You are at the boulangerie and
they forgot your order." A TTS interlocutor (examiner voice) responds
to the learner across 2–3 turns. The session route owns the
multi-turn TTS rendering; the drill itself grades the learner's
*aggregate* recording (concatenated audio of their turns).
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._eo_common import grade_eo_recording
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

_TOTAL_S: Final[int] = 90


class EORoleplayDrill(Drill):
    """Role-play drill with TTS interlocutor. Phase 7 scores."""

    spec = DrillSpec(
        drill_kind="eo_roleplay",
        module="EO",
        requires_audio_in=True,
        requires_audio_out=True,  # examiner TTS responds across turns
        rubric_pending=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the scenario + the interlocutor turn script."""
        content = item.content
        assert isinstance(content, EOContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="eo_roleplay",
            expected_rt_ms=_TOTAL_S * 1000,
            payload={
                "examiner_prompts": list(content.examiner_prompts),
                "target_duration_s": _TOTAL_S,
                "rubric_version": content.rubric_version,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Grade the aggregated learner-turn recording."""
        content = item.content
        assert isinstance(content, EOContent)
        return grade_eo_recording(
            response,
            drill_kind="eo_roleplay",
            rubric_version=content.rubric_version,
        )


__all__ = ["EORoleplayDrill"]
