"""EE supplementary drill — register adjustment (`phase5_design.md §4.3`).

Given a message at one register (e.g. familier), rewrite at another
(soutenu / formal). Same Phase 5 posture as `ee_rewrite`: the
pipeline collects the response + word count and emits a rubric-pending
`Interaction`; the Phase 7 scorer evaluates register-shift accuracy.

The drill consumes `EEContent` and treats the item's `prompt` as the
source text + target-register instruction. The bank ships register-
specific items under separate ids; the planner picks them via the
finer-grained `DrillType="ee_register_adjust"`.
"""

from __future__ import annotations

from tcf_accel.schemas.content import EEContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._ee_common import count_words
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep


class EERegisterAdjustDrill(Drill):
    """Register-adjustment drill (familier ↔ soutenu). Phase 7 scores."""

    spec = DrillSpec(
        drill_kind="ee_register_adjust",
        module="EE",
        rubric_pending=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the source text + the target-register cue."""
        content = item.content
        assert isinstance(content, EEContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="ee_register_adjust",
            single_play=False,
            payload={
                "source_prompt": content.prompt,
                "rubric_version": content.rubric_version,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Emit a rubric-pending result tagged for the Phase 7 register scorer."""
        content = item.content
        assert isinstance(content, EEContent)
        text = str(response.get("text", ""))
        return DrillResult(
            correct=None,
            raw_response={"text": text, "word_count": count_words(text)},
            graded_score={
                "pending": True,
                "drill_origin": "ee_register_adjust",
                "rubric_version": content.rubric_version,
                "word_count": count_words(text),
                "phase7_status": "stub",
            },
        )


__all__ = ["EERegisterAdjustDrill"]
