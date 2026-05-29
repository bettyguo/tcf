"""CO core drill — single-play MCQ (`phase5_design.md §4.1`, ADR-029).

The TCF Canada CO plays each clip **once**. The drill enforces this as a
presentation contract: `DrillStep.single_play` is True, and the UI
renders the audio element with no scrubbing and gates any replay
affordance behind submission (the structural enforcement lives in the
Phase 8 player; the spec flag is the contract).

Grading is MCQ correctness on the item's first question (the exam's CO
items are single-question). The exam-pace per-item budget is the audio
length plus a 20 s answer window; `present` surfaces it as
`expected_rt_ms` for the soft timer.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import COContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep, grade_mcq

_ANSWER_WINDOW_S: Final[int] = 20


class COMCQDrill(Drill):
    """Single-play CO multiple-choice drill."""

    spec = DrillSpec(
        drill_kind="co_mcq",
        module="CO",
        requires_audio_in=False,  # the *item* carries audio; the learner doesn't record
        single_play=True,
        exam_pace_default_s_per_item=None,  # computed per item (audio + window)
        accessibility_alt="co_lexical_alt",
    )

    def present(self, item: Item) -> DrillStep:
        """Render the single-play CO item; the transcript is withheld pre-answer."""
        content = item.content
        assert isinstance(content, COContent)
        budget_s = content.duration_s + _ANSWER_WINDOW_S
        return DrillStep(
            item_id=item.id,
            drill_kind="co_mcq",
            single_play=True,
            expected_rt_ms=int(budget_s * 1000),
            payload={
                "audio_local_path": content.audio_local_path,
                "duration_s": content.duration_s,
                "question_id": content.questions[0].id,
                # The transcript is withheld until *after* answering (ADR-029);
                # the UI fetches it via the review endpoint, not from this payload.
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Grade the chosen option; record the replay count for the audit."""
        content = item.content
        assert isinstance(content, COContent)
        question = content.questions[0]
        correct = grade_mcq(question, response)
        chosen = response.get("option_id", response.get("answer"))
        replays = int(response.get("audio_replays", 0) or 0)
        return DrillResult(
            correct=correct,
            raw_response={
                "option_id": chosen,
                "question_id": question.id,
                "audio_replays": replays,
            },
        )


__all__ = ["COMCQDrill"]
