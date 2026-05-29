"""CO supplementary drill — gap-fill from audio (`phase5_design.md §4.1`).

The transcript is shown with N gaps; the audio plays once; the learner
types the missing words. Tests phonological recognition + spelling.

The gaps are derived deterministically from the transcript (every
`_GAP_STRIDE`-th word, capped at `_MAX_GAPS`), so `present` and `grade`
agree on the answer key without storing per-session state. Grading is
per-gap exact match (accent- and case-insensitive); the item is correct
iff every gap is filled correctly.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import COContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._text import normalize_token, tokenize
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

_GAP_STRIDE: Final[int] = 3
_MAX_GAPS: Final[int] = 7


def _gap_indices(n_tokens: int) -> list[int]:
    """Indices of the words to blank: every stride-th word, capped."""
    return list(range(_GAP_STRIDE - 1, n_tokens, _GAP_STRIDE))[:_MAX_GAPS]


class COGapFillDrill(Drill):
    """Gap-fill-from-audio drill."""

    spec = DrillSpec(
        drill_kind="co_gapfill",
        module="CO",
        single_play=True,
    )

    def _key(self, item: Item) -> tuple[list[str], list[int]]:
        content = item.content
        assert isinstance(content, COContent)
        tokens = tokenize(content.transcript)
        gaps = _gap_indices(len(tokens))
        answers = [tokens[i] for i in gaps]
        return answers, gaps

    def present(self, item: Item) -> DrillStep:
        """Render the gapped transcript; gap positions are the answer key."""
        content = item.content
        assert isinstance(content, COContent)
        tokens = tokenize(content.transcript)
        _, gaps = self._key(item)
        gap_set = set(gaps)
        masked = ["____" if i in gap_set else t for i, t in enumerate(tokens)]
        return DrillStep(
            item_id=item.id,
            drill_kind="co_gapfill",
            single_play=True,
            payload={
                "audio_local_path": content.audio_local_path,
                "masked_transcript": " ".join(masked),
                "n_gaps": len(gaps),
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Score per-gap exact match; correct iff all gaps are right."""
        answers, _ = self._key(item)
        raw = response.get("answers", [])
        submitted = [str(a) for a in raw] if isinstance(raw, list) else []
        per_gap = [
            i < len(submitted) and normalize_token(submitted[i]) == normalize_token(ans)
            for i, ans in enumerate(answers)
        ]
        n_right = sum(per_gap)
        total = len(answers)
        return DrillResult(
            correct=total > 0 and n_right == total,
            partial_credit=(n_right / total) if total else 0.0,
            raw_response={
                "answers": submitted,
                "per_gap_correct": per_gap,
                "n_gaps": total,
            },
        )


__all__ = ["COGapFillDrill"]
