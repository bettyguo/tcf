"""EO supplementary drill — picture description (`phase5_design.md §4.4`).

30 s prep + 90 s production. Tests lexical access under pressure.

Phase 5 ships the rubric-pending pipeline; the bank's image attachment
lands with the §17 step 14 quality-gate work (EOContent does not
currently model image URLs — the prompt text describes the image).
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._eo_common import grade_eo_recording
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

_PREP_S: Final[int] = 30
_PRODUCTION_S: Final[int] = 90


class EOPictureDrill(Drill):
    """Picture-description drill. Phase 7 scores."""

    spec = DrillSpec(
        drill_kind="eo_picture",
        module="EO",
        requires_audio_in=True,
        rubric_pending=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the prompt + the 30 s prep / 90 s production timings."""
        content = item.content
        assert isinstance(content, EOContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="eo_picture",
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
            drill_kind="eo_picture",
            rubric_version=content.rubric_version,
        )


__all__ = ["EOPictureDrill"]
