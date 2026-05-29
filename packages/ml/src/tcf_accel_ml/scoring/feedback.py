"""Learner-facing feedback rendering.

The render obeys the THINK doc §8.4 anti-criterion: any quoted-back
learner text is carried in `FeedbackBlock.learner_quote` (the UI is
required to style it as a blockquote), never inlined into `detail`.

Each block has a `kind` (strength / fix / context / disclaimer), a
short headline, a one-sentence detail, an optional learner-quote
fragment, and an optional drill id linking back into the Phase 5
drill catalogue.

The render is **deterministic**: same rubric+features in → same blocks
out. Tests assert this.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from tcf_accel.schemas.content.ee import ErrorAnnotation
from tcf_accel.schemas.scoring import SpeakingRubric, WritingRubric

from tcf_accel_ml.scoring.features.speaking import SpeakingFeatures
from tcf_accel_ml.scoring.features.writing import WritingFeatures
from tcf_accel_ml.scoring.rubric_table import nclc_from_total_20

FeedbackKind = Literal["strength", "fix", "context", "disclaimer"]


@dataclass(frozen=True)
class FeedbackBlock:
    kind: FeedbackKind
    headline: str
    detail: str
    learner_quote: str | None = None
    drill_id: str | None = None


# Error-type → drill id mapping. Phase 5 owns the drill catalogue;
# Phase 7 only stores a stable mapping into it.
_ERROR_TYPE_DRILLS: dict[str, str] = {
    "agreement": "ee-agreement-c1",
    "tense": "ee-si-clause-types",
    "preposition": "ee-prepositions-fr",
    "article": "ee-articles-genre",
    "spelling": "ee-spelling-frequent",
    "vocabulary": "ee-lexicon-c1",
    "syntax": "ee-syntax-c1",
    "register": "ee-register-soutenu",
    "cohesion": "ee-connectors-c1",
    "other": "ee-mixed-review",
}

_PRONUNCIATION_DISCLAIMER = (
    "Auto-feedback is approximate. A trained examiner could see more. "
    "Pronunciation scoring uses a coarse proxy (ADR-031)."
)


def _strengths_from_writing(
    rubric: WritingRubric, features: WritingFeatures,
) -> list[FeedbackBlock]:
    blocks: list[FeedbackBlock] = []
    if features.moving_average_ttr_25 >= 0.55:
        blocks.append(
            FeedbackBlock(
                kind="strength",
                headline="Lexical range is solid",
                detail=f"MATTR-25 of {features.moving_average_ttr_25:.2f} signals a varied vocabulary.",
            )
        )
    if features.distinct_discourse_categories >= 3:
        blocks.append(
            FeedbackBlock(
                kind="strength",
                headline="Clear discourse moves",
                detail=(
                    f"You used {features.distinct_discourse_categories} distinct "
                    "categories of connectors — that helps coherence."
                ),
            )
        )
    if features.canadian_lexicon_density > 0.02:
        blocks.append(
            FeedbackBlock(
                kind="strength",
                headline="Canadian context integrated",
                detail="Your response references Canadian-specific elements — the rubric rewards this.",
            )
        )
    return blocks


def _fixes_from_errors(
    text: str,
    errors: Sequence[ErrorAnnotation],
    *,
    target_nclc: int,
    cap: int = 3,
) -> list[FeedbackBlock]:
    """Top-N fixes from the error list, deduplicated by error_type.

    Errors are ranked by descending confidence; ties broken by earlier
    span. Each fix gets the learner's quoted span (the UI renders it
    as a blockquote — never as our prose).
    """
    seen_types: set[str] = set()
    fixes: list[FeedbackBlock] = []
    ranked = sorted(
        errors,
        key=lambda e: (-e.confidence, e.span_start),
    )
    for err in ranked:
        if len(fixes) >= cap:
            break
        if err.error_type in seen_types:
            continue
        seen_types.add(err.error_type)
        quote = text[err.span_start : err.span_end]
        suggestion = err.suggestion or "see a trained examiner"
        headline = f"({err.error_type.title()}) {suggestion}"
        detail = (
            f"Targeting NCLC {target_nclc}: this error class drops the "
            f"grammatical-accuracy / register score by ~0.5–1 each occurrence."
        )
        fixes.append(
            FeedbackBlock(
                kind="fix",
                headline=headline,
                detail=detail,
                learner_quote=quote,
                drill_id=_ERROR_TYPE_DRILLS.get(err.error_type),
            )
        )
    return fixes


def _context_block(rubric: WritingRubric | SpeakingRubric, target_nclc: int) -> FeedbackBlock:
    nclc = nclc_from_total_20(rubric.total_20)
    return FeedbackBlock(
        kind="context",
        headline=f"Total {rubric.total_20}/20 — NCLC ≈ {nclc}",
        detail=(
            f"Your target is NCLC {target_nclc}. "
            f"Closing the gap is most efficiently done via the linked drills below."
        ),
    )


def render_feedback(
    *,
    rubric: WritingRubric | SpeakingRubric,
    features: WritingFeatures | SpeakingFeatures,
    text: str = "",
    errors: Sequence[ErrorAnnotation] | None = None,
    target_nclc: int = 9,
    is_speaking: bool = False,
) -> list[FeedbackBlock]:
    """Render feedback blocks. Deterministic.

    Args:
        rubric: The graded `WritingRubric` or `SpeakingRubric`.
        features: The corresponding feature vector.
        text: The source text or transcript (used to extract
            learner-quote fragments for fix blocks).
        errors: Deduped error annotations. Defaults to `rubric.error_list`
            for `WritingRubric`; empty for `SpeakingRubric`.
        target_nclc: The learner's target NCLC band.
        is_speaking: Whether to append the pronunciation disclaimer.
    """
    errs = list(errors) if errors is not None else getattr(rubric, "error_list", [])
    writing_features = (
        features.writing if isinstance(features, SpeakingFeatures) else features
    )
    blocks: list[FeedbackBlock] = []
    blocks.append(_context_block(rubric, target_nclc))
    blocks.extend(_strengths_from_writing(rubric, writing_features))
    blocks.extend(_fixes_from_errors(text, errs, target_nclc=target_nclc))
    if is_speaking:
        blocks.append(
            FeedbackBlock(
                kind="disclaimer",
                headline="Pronunciation is a coarse proxy",
                detail=_PRONUNCIATION_DISCLAIMER,
            )
        )
    else:
        blocks.append(
            FeedbackBlock(
                kind="disclaimer",
                headline="Auto-feedback is approximate",
                detail="A trained examiner could see more than the auto-scorer.",
            )
        )
    return blocks


__all__ = ["FeedbackBlock", "FeedbackKind", "render_feedback"]
