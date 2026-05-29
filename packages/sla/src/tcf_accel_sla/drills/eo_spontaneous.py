"""EO supplementary drill — spontaneous opinion (`phase5_design.md §4.4`).

5 s prep + 60 s production. Prompt appears, learner has 5 s to begin
speaking. Tests fluency under minimal preparation.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._eo_common import grade_eo_recording
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

_PREP_S: Final[int] = 5
_PRODUCTION_S: Final[int] = 60


class EOSpontaneousDrill(Drill):
    """Spontaneous-opinion drill. Phase 7 scores."""

    spec = DrillSpec(
        drill_kind="eo_spontaneous",
        module="EO",
        requires_audio_in=True,
        rubric_pending=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the prompt + the 5 s prep / 60 s production timings."""
        content = item.content
        assert isinstance(content, EOContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="eo_spontaneous",
            expected_rt_ms=(_PREP_S + _PRODUCTION_S) * 1000,
            payload={
                "examiner_prompts": list(content.examiner_prompts),
                "candidate_prep_time_s": _PREP_S,
                "target_duration_s": _PRODUCTION_S,
                "rubric_version": content.rubric_version,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Run the audio pipeline; emit a rubric-pending result."""
        content = item.content
        assert isinstance(content, EOContent)
        return grade_eo_recording(
            response,
            drill_kind="eo_spontaneous",
            rubric_version=content.rubric_version,
        )


__all__ = ["EOSpontaneousDrill"]
