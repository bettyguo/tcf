"""EE core drill — 3-task timed write (`phase5_design.md §4.3`).

Phase 5 ships the *pipeline*: accept a text response, compute the word
count + word-count penalty, emit an `Interaction` whose `correct` is
`None` (rubric pending) and whose `graded_score` carries the metadata
the Phase 7 rubric scorer will consume.

The drill is parametric on `task_number` via the item's `EEContent`
(task 1/2/3). The word-count target comes from the item's
`target_word_count_range`; the FEI 60/120/180 canonical lives in
`_ee_common.WORD_COUNT_TARGETS` and the audit asserts the bank's
ranges match.
"""

from __future__ import annotations

from tcf_accel.schemas.content import EEContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._ee_common import (
    WORD_COUNT_TARGETS,
    count_words,
    in_word_band,
    word_count_penalty,
)
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

# Per-task time budgets (FEI: 10 / 20 / 30 min for tasks 1/2/3).
_PREP_AND_WRITE_S: dict[int, int] = {1: 600, 2: 1200, 3: 1800}


class EETaskDrill(Drill):
    """Timed 3-task write. Phase 7 scores the rubric; Phase 5 emits pending."""

    spec = DrillSpec(
        drill_kind="ee_task",
        module="EE",
        rubric_pending=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the prompt + target word range + per-task time budget."""
        content = item.content
        assert isinstance(content, EEContent)
        low, high = content.target_word_count_range
        return DrillStep(
            item_id=item.id,
            drill_kind="ee_task",
            single_play=False,
            expected_rt_ms=_PREP_AND_WRITE_S.get(content.task_number, 1200) * 1000,
            payload={
                "task_number": content.task_number,
                "prompt": content.prompt,
                "target_word_count_low": low,
                "target_word_count_high": high,
                "required_canadian_context": content.required_canadian_context,
                "rubric_version": content.rubric_version,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Emit a rubric-pending result with word-count metadata for Phase 7."""
        content = item.content
        assert isinstance(content, EEContent)
        text = str(response.get("text", ""))
        word_count = count_words(text)
        target = WORD_COUNT_TARGETS[content.task_number]
        penalty = word_count_penalty(word_count, target)
        in_band = in_word_band(word_count, target)
        return DrillResult(
            correct=None,  # rubric pending — Phase 7 fills this in
            partial_credit=None,
            raw_response={
                "text": text,
                "word_count": word_count,
                "task_number": content.task_number,
            },
            graded_score={
                "pending": True,
                "task_number": content.task_number,
                "rubric_version": content.rubric_version,
                "word_count": word_count,
                "word_count_target": target,
                "word_count_penalty": penalty,
                "in_word_band": in_band,
                "phase7_status": "stub",
            },
        )


__all__ = ["EETaskDrill"]
