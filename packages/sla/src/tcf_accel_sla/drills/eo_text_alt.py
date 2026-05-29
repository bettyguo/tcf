"""EO accessibility alternative — text-input (`phase5_design.md §7`).

For learners who cannot or do not wish to record. The drill consumes an
`EOContent` item but accepts a *text* response in place of audio. The
load-bearing property: this drill declares `module="EE"`, so its
interactions update the EE (production) posterior, **not** EO. The UI
banner is mandatory ("This does not measure real EO").

Symmetric to `co_lexical_alt` (ADR-029). The contract is the same
shape — emit a `drill_origin` tag so the audit can detect the routing,
and never write `module="EO"` from this drill.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._ee_common import count_words
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

_BANNER_KEY: Final[str] = "eo_text_alt"


class EOTextAltDrill(Drill):
    """Text-input alternative for the EO drill (accessibility)."""

    spec = DrillSpec(
        drill_kind="eo_text_alt",
        module="EE",  # ADR-029-shape: updates the EE posterior, never EO.
        rubric_pending=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the EO prompt as text + the mandatory a11y banner."""
        content = item.content
        assert isinstance(content, EOContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="eo_text_alt",
            payload={
                "examiner_prompts": list(content.examiner_prompts),
                "rubric_version": content.rubric_version,
                "accessibility_banner_key": _BANNER_KEY,
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Grade the text response (rubric pending); tag drill_origin for audit."""
        content = item.content
        assert isinstance(content, EOContent)
        text = str(response.get("text", ""))
        return DrillResult(
            correct=None,
            raw_response={"text": text, "word_count": count_words(text)},
            graded_score={
                "pending": True,
                "phase7_status": "stub",
                "drill_origin": "eo_text_alt",
                "rubric_version": content.rubric_version,
                "word_count": count_words(text),
            },
        )


__all__ = ["EOTextAltDrill"]
