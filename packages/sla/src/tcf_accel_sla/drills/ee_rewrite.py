"""EE supplementary drill — sentence rewriting (`phase5_design.md §4.3`).

Learner is given a sentence at NCLC 7 register and asked to rewrite at
NCLC 9 (more sophisticated lexis, complex syntax). The drill is
rubric-pending in Phase 5: it consumes the same `EEContent` shape as
`ee_task`, treats the item's `prompt` as the source sentence + target
register, and emits an `Interaction` whose `graded_score` flags it for
the Phase 7 rubric scorer.

The grade differs from `ee_task` in two ways:
- The word-count check is *informational*, not gated (a rewrite is
  one sentence; the penalty math doesn't apply).
- The drill_kind in the emitted row lets the Phase 7 scorer route to
  the sentence-rewriting rubric variant.
"""

from __future__ import annotations

from tcf_accel.schemas.content import EEContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._ee_common import count_words
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep


class EERewriteDrill(Drill):
    """Sentence-rewriting drill (NCLC 7 → NCLC 9). Phase 7 scores."""

    spec = DrillSpec(
        drill_kind="ee_rewrite",
        module="EE",
        rubric_pending=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the source sentence + target-register hint."""
        content = item.content
        assert isinstance(content, EEContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="ee_rewrite",
            single_play=False,
            payload={
                "source_prompt": content.prompt,
                "rubric_version": content.rubric_version,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Emit a rubric-pending result with the rewritten text + word count."""
        content = item.content
        assert isinstance(content, EEContent)
        text = str(response.get("text", ""))
        return DrillResult(
            correct=None,
            raw_response={"text": text, "word_count": count_words(text)},
            graded_score={
                "pending": True,
                "drill_origin": "ee_rewrite",
                "rubric_version": content.rubric_version,
                "word_count": count_words(text),
                "phase7_status": "stub",
            },
        )


__all__ = ["EERewriteDrill"]
