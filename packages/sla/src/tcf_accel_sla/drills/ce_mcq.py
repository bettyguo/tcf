"""CE core drill — timed-passage MCQ (`phase5_design.md §4.2`).

Passage + question + 4 options on one screen; a 60 s soft per-item
budget. The drill captures `time_to_first_answer_ms` and a coarse
scroll-position proxy in `raw_response` (the spec's approximation of
eye-tracking); Phase 8 wires the actual scroll telemetry.

Grading is MCQ correctness on the item's first question.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import CEContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep, grade_mcq

_SOFT_BUDGET_S: Final[int] = 60


class CEMCQDrill(Drill):
    """Timed-passage CE multiple-choice drill."""

    spec = DrillSpec(
        drill_kind="ce_mcq",
        module="CE",
        exam_pace_default_s_per_item=_SOFT_BUDGET_S,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the passage + question with the 60 s soft per-item budget."""
        content = item.content
        assert isinstance(content, CEContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="ce_mcq",
            single_play=False,
            expected_rt_ms=_SOFT_BUDGET_S * 1000,
            payload={
                "passage": content.passage,
                "word_count": content.word_count,
                "genre": content.genre,
                "question_id": content.questions[0].id,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Grade the chosen option; capture time-to-first-answer + scroll depth."""
        content = item.content
        assert isinstance(content, CEContent)
        question = content.questions[0]
        correct = grade_mcq(question, response)
        chosen = response.get("option_id", response.get("answer"))
        return DrillResult(
            correct=correct,
            raw_response={
                "option_id": chosen,
                "question_id": question.id,
                "time_to_first_answer_ms": response.get("time_to_first_answer_ms"),
                "scroll_depth": response.get("scroll_depth"),
            },
        )


__all__ = ["CEMCQDrill"]
