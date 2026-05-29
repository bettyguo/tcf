"""CO accessibility alternative — lexical drill (ADR-029, `phase5_design.md §7`).

For Deaf / hard-of-hearing learners. Presents a CO item's transcript
*as text* and grades the same MCQ as a lexical-comprehension probe.

The load-bearing property: this drill declares `module="CE"`, so its
interactions update the CE (reading/lexical) posterior and **never**
the CO posterior. A CO estimate must mean "heard the audio once," not
"read the transcript" — mixing the two would collapse the meaning of
the CO posterior (`phase5_think.md §1.1`). The UI carries a mandatory
banner ("does not measure CO; does not contribute to your CO NCLC
estimate").

`raw_response.drill_origin = "co_lexical_alt"` lets the audit detect
the routing; the DB CHECK constraint (`interactions_lexical_alt_module_ck`)
enforces `drill_kind='co_lexical_alt' ⟹ module='CE'` at the storage layer.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import COContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep, grade_mcq

_BANNER_KEY: Final[str] = "co_lexical_alt"


class COLexicalAltDrill(Drill):
    """Text-presented lexical drill over a CO item (accessibility alt)."""

    spec = DrillSpec(
        drill_kind="co_lexical_alt",
        module="CE",  # ADR-029: updates the CE posterior, never CO.
    )

    def present(self, item: Item) -> DrillStep:
        """Render the CO transcript as text with the mandatory a11y banner."""
        content = item.content
        assert isinstance(content, COContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="co_lexical_alt",
            single_play=False,
            payload={
                "transcript": content.transcript,
                "question_id": content.questions[0].id,
                "accessibility_banner_key": _BANNER_KEY,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Grade the MCQ; tag the row with `drill_origin` for the audit."""
        content = item.content
        assert isinstance(content, COContent)
        question = content.questions[0]
        correct = grade_mcq(question, response)
        chosen = response.get("option_id", response.get("answer"))
        return DrillResult(
            correct=correct,
            raw_response={
                "option_id": chosen,
                "question_id": question.id,
                "drill_origin": "co_lexical_alt",
            },
        )


__all__ = ["COLexicalAltDrill"]
