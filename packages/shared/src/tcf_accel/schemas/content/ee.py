"""EE (Expression écrite) item content + `ErrorAnnotation`.

A EE item is a writing prompt (one of three TCF Canada task numbers)
plus the rubric version pinned per release. The candidate's response
is graded asynchronously (Phase 7); `ErrorAnnotation` is the structured
span the rubric scorer attaches to a graded response.

`ErrorAnnotation` is exported here because both `EEContent` (canonical
prompts may pre-annotate model answers) and `WritingRubric` (graded
output) reference it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

ErrorType = Literal[
    "spelling",
    "agreement",
    "tense",
    "preposition",
    "article",
    "syntax",
    "register",
    "vocabulary",
    "cohesion",
    "other",
]


class ErrorAnnotation(BaseModel):
    """A spanned error in a learner's writing or speaking transcript."""

    model_config = ConfigDict(extra="forbid")

    span_start: int = Field(ge=0)
    span_end: int = Field(ge=0)
    error_type: ErrorType
    suggestion: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _span_invariant(self) -> Self:
        if self.span_end < self.span_start:
            msg = f"span_end={self.span_end} < span_start={self.span_start}"
            raise ValueError(msg)
        return self


class EEContent(BaseModel):
    """Expression écrite item content.

    Example:
        >>> EEContent(
        ...     task_number=2,
        ...     prompt="Vous écrivez à votre voisin pour vous plaindre du bruit.",
        ...     target_word_count_range=(120, 150),
        ...     required_canadian_context=True,
        ...     rubric_version='ee.v1',
        ... ).module
        'EE'
    """

    model_config = ConfigDict(extra="forbid")

    module: Literal["EE"] = "EE"
    task_number: Literal[1, 2, 3]
    prompt: str = Field(min_length=1)
    target_word_count_range: tuple[int, int] = Field(
        description="(min, max) word count expected for a complete response.",
    )
    required_canadian_context: bool = Field(
        description="True for Task 2 and Task 3 per TCF Canada spec.",
    )
    rubric_version: str = Field(
        min_length=1,
        description="Pinned per release; the Phase 7 rubric scorer uses this to select the correct prompt template.",
    )

    @model_validator(mode="after")
    def _word_count_range_invariant(self) -> Self:
        lo, hi = self.target_word_count_range
        if lo <= 0 or hi <= 0:
            msg = f"word counts must be positive: {self.target_word_count_range}"
            raise ValueError(msg)
        if lo > hi:
            msg = f"target_word_count_range min={lo} > max={hi}"
            raise ValueError(msg)
        return self


__all__ = ["EEContent", "ErrorAnnotation", "ErrorType"]
