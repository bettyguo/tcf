"""Length-balance quality check for MCQ distractors.

Per `phase3_design.md §5.3` and R-003: synthesized distractors must be
within ±25% of the correct option's token length, otherwise the
"correct option is always the longest" tell becomes detectable to
sufficiently-strategic learners.

This module ships a P1 check (flag, do not reject) using whitespace
tokenisation as a Phase-3-foundation approximation. The Phase 3
follow-up that wires the LLM synthesizers swaps in CamemBERT
tokenisation for a sharper count, but the ±25% threshold itself stays
the same (ADR-adjacent decision recorded in `phase3_design.md §3`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tcf_accel.schemas import CEContent, COContent, Item

from tcf_accel_content.quality import DISTRACTOR_LENGTH_TOLERANCE
from tcf_accel_content.types import QualityCheckResult


def _token_count(text: str) -> int:
    """Whitespace tokenisation. Phase 3 follow-up upgrades to CamemBERT."""
    return len(text.split())


@dataclass(frozen=True)
class LengthBalancedDistractorsCheck:
    """P1 check: every distractor's token count is within ±tolerance.

    The check runs only on MCQ-bearing modules (CO, CE). For EE/EO it
    short-circuits to ``passed=True`` with an ``info`` severity, since
    those modules carry no distractors.

    Example:
        >>> from datetime import UTC, datetime
        >>> from uuid import uuid4
        >>> from tcf_accel.ids import ItemId
        >>> from tcf_accel.schemas import (
        ...     CEContent, Item, MCQ, MCQOption, Provenance,
        ... )
        >>> def _item(opts: list[tuple[str, str]]) -> Item:
        ...     return Item(
        ...         id=ItemId(uuid4()), module="CE", cefr_level="B2",
        ...         content=CEContent(
        ...             passage="x" * 60, genre="news", word_count=12,
        ...             questions=[MCQ(
        ...                 id="q1", prompt="?",
        ...                 options=[MCQOption(id=i, text=t) for i, t in opts],
        ...                 correct_option_id="a",
        ...             )],
        ...         ),
        ...         provenance=Provenance(
        ...             source="x", source_id="1", license="CC0-1.0",
        ...             ingested_at=datetime(2026,1,1,tzinfo=UTC),
        ...         ),
        ...     )
        >>> chk = LengthBalancedDistractorsCheck()
        >>> chk(_item([("a","one two three four"),
        ...            ("b","four five six seven"),
        ...            ("c","eight nine ten eleven"),
        ...            ("d","twelve thirteen fourteen fifteen")])).passed
        True
        >>> chk(_item([("a","one two three four five six seven eight"),
        ...            ("b","tiny"),
        ...            ("c","also short"),
        ...            ("d","equally tiny")])).passed
        False

    Complexity: O(total option text length).
    """

    name: str = "length_balanced_distractors"
    severity: Literal["P0", "P1"] = "P1"
    tolerance: float = DISTRACTOR_LENGTH_TOLERANCE

    def __call__(self, item: Item) -> QualityCheckResult:
        """Run the check; see class docstring."""
        content = item.content
        if not isinstance(content, COContent | CEContent):
            return QualityCheckResult(
                name=self.name, passed=True, severity="info",
                detail=f"module={item.module} has no distractors",
            )

        worst_delta = 0.0
        for question in content.questions:
            correct = next(
                (o for o in question.options if o.id == question.correct_option_id),
                None,
            )
            if correct is None:
                return QualityCheckResult(
                    name=self.name, passed=False, severity=self.severity,
                    detail=f"question {question.id}: correct_option_id missing from options",
                )
            correct_len = _token_count(correct.text)
            if correct_len == 0:
                return QualityCheckResult(
                    name=self.name, passed=False, severity=self.severity,
                    detail=f"question {question.id}: correct option is empty",
                )
            for distractor in question.options:
                if distractor.id == question.correct_option_id:
                    continue
                d_len = _token_count(distractor.text)
                delta = abs(d_len - correct_len) / correct_len
                worst_delta = max(worst_delta, delta)

        worst_pct = f"{worst_delta:.2%}"
        tol_pct = f"{self.tolerance:.0%}"
        if worst_delta <= self.tolerance:
            return QualityCheckResult(
                name=self.name, passed=True, severity=self.severity,
                detail=f"worst distractor length delta={worst_pct} <= tolerance={tol_pct}",
                metric=worst_delta,
            )
        return QualityCheckResult(
            name=self.name, passed=False, severity=self.severity,
            detail=f"worst distractor length delta={worst_pct} > tolerance={tol_pct}",
            metric=worst_delta,
        )


__all__ = ["LengthBalancedDistractorsCheck"]
