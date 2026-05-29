"""CO supplementary drill — dictation (`phase5_design.md §4.1`).

A short single-play utterance; the learner transcribes it; we measure
WER against the item's ground-truth transcript and classify the error
shapes. Correctness is a WER threshold (≤ 0.15 → correct); the richer
signal is `partial_credit = 1 - WER` and the error-class breakdown.

The error classifier is rule-based on the token alignment. The
`register` class needs the Phase 3 register classifier and is stubbed
(never emitted) until that's wired; the structural shapes
(missing/extra/substitution) are computed here.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.content import COContent
from tcf_accel.schemas.item import Item

from tcf_accel_sla.drills._text import normalized_tokens, word_error_rate
from tcf_accel_sla.drills.base import Drill, DrillResult, DrillSpec, DrillStep

_CORRECT_WER_MAX: Final[float] = 0.15


def _classify_errors(reference: str, hypothesis: str) -> list[str]:
    """Coarse error-shape labels from a token multiset comparison.

    `missing`  — reference has words the hypothesis lacks.
    `extra`    — hypothesis has words not in the reference.
    `spelling` — same word count but token mismatches remain after
                 accounting for missing/extra (a proxy; true spelling
                 vs lexical errors need the Phase 7 annotator).
    """
    ref = normalized_tokens(reference)
    hyp = normalized_tokens(hypothesis)
    ref_set, hyp_set = set(ref), set(hyp)
    labels: list[str] = []
    if ref_set - hyp_set:
        labels.append("missing")
    if hyp_set - ref_set:
        labels.append("extra")
    if len(ref) == len(hyp) and ref != hyp and not (ref_set - hyp_set):
        labels.append("spelling")
    return labels


class CODictationDrill(Drill):
    """Single-play dictation drill."""

    spec = DrillSpec(
        drill_kind="co_dictation",
        module="CO",
        single_play=True,
    )

    def present(self, item: Item) -> DrillStep:
        """Render the dictation prompt; the transcript is the hidden answer key."""
        content = item.content
        assert isinstance(content, COContent)
        return DrillStep(
            item_id=item.id,
            drill_kind="co_dictation",
            single_play=True,
            payload={
                "audio_local_path": content.audio_local_path,
                "duration_s": content.duration_s,
                "n_reference_words": len(normalized_tokens(content.transcript)),
            },
        )

    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Score the transcription by WER and classify the error shapes."""
        content = item.content
        assert isinstance(content, COContent)
        transcription = str(response.get("transcription", ""))
        wer = word_error_rate(content.transcript, transcription)
        return DrillResult(
            correct=wer <= _CORRECT_WER_MAX,
            partial_credit=max(0.0, 1.0 - wer),
            raw_response={
                "transcription": transcription,
                "wer": wer,
                "error_classes": _classify_errors(content.transcript, transcription),
            },
        )


__all__ = ["CODictationDrill"]
