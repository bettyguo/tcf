"""Gate composer: run an ordered list of `QualityCheck`s and emit a verdict.

The gate is intentionally a thin reducer. Each check is independent and
ordered cheapest-first by the caller (`phase3_design.md §5.1`). The
gate stops on no check — every check runs so the audit trail is
complete — but the *verdict* is determined by the failure severities:

- One or more P0 failures   → ``"reject"`` (item does not enter the bank)
- No P0 failures, ≥ 1 P1 failure → ``"p1_flag"`` (item enters the bank but
  carries `NEEDS_HUMAN_REVIEW` so the scheduler can exclude it until
  reviewed)
- All checks pass          → ``"pass"``

This module also exposes a default `phase3_foundation_checks()` factory
that returns the two foundation-grade checks shipped in this slice
(`LicenseCompatibleCheck`, `LengthBalancedDistractorsCheck`). The real
Phase 3 follow-up extends the tuple with adversarial, dup, PII,
acoustic, etc.; the gate composer itself does not change.
"""

from __future__ import annotations

from collections.abc import Sequence

from tcf_accel.schemas import Item, QualityFlag

from tcf_accel_content.quality import QualityCheck
from tcf_accel_content.quality.length import LengthBalancedDistractorsCheck
from tcf_accel_content.quality.license_check import LicenseCompatibleCheck
from tcf_accel_content.types import QualityCheckResult, QualityReport


def run_gate(item: Item, checks: Sequence[QualityCheck]) -> QualityReport:
    """Run every check on `item` and reduce to a single `QualityReport`.

    Every check runs even after a P0 failure so the operator gets the
    complete audit trail. Verdict is determined by the most-severe
    failing check.

    Args:
        item: A Pydantic-valid `Item` (typically a `CandidateItem.item`
            from a synthesizer).
        checks: The check sequence to run, ordered cheapest-first by
            the caller. Repeating a check name is allowed but odd —
            the gate makes no de-dup attempt.

    Returns:
        A `QualityReport` carrying every check's result and an overall
        verdict.

    Example:
        >>> from datetime import UTC, datetime
        >>> from uuid import uuid4
        >>> from tcf_accel.ids import ItemId
        >>> from tcf_accel.schemas import (
        ...     CEContent, Item, MCQ, MCQOption, Provenance,
        ... )
        >>> item = Item(
        ...     id=ItemId(uuid4()), module="CE", cefr_level="B2",
        ...     content=CEContent(
        ...         passage=" ".join(["lorem"] * 30),
        ...         genre="news", word_count=30,
        ...         questions=[MCQ(id="q1", prompt="?",
        ...             options=[MCQOption(id="a", text="aa bb cc"),
        ...                      MCQOption(id="b", text="dd ee ff"),
        ...                      MCQOption(id="c", text="gg hh ii"),
        ...                      MCQOption(id="d", text="jj kk ll")],
        ...             correct_option_id="a")],
        ...     ),
        ...     provenance=Provenance(
        ...         source="x", source_id="1", license="CC0-1.0",
        ...         ingested_at=datetime(2026,1,1,tzinfo=UTC),
        ...     ),
        ... )
        >>> report = run_gate(item, phase3_foundation_checks())
        >>> report.verdict
        'pass'

    Complexity: O(sum of check costs).
    """
    results: list[QualityCheckResult] = []
    has_p0_failure = False
    has_p1_failure = False
    flags: list[str] = []
    for check in checks:
        result = check(item)
        results.append(result)
        if not result.passed:
            if result.severity == "P0":
                has_p0_failure = True
            elif result.severity == "P1":
                has_p1_failure = True
                if QualityFlag.NEEDS_HUMAN_REVIEW.value not in flags:
                    flags.append(QualityFlag.NEEDS_HUMAN_REVIEW.value)

    if has_p0_failure:
        verdict = "reject"
    elif has_p1_failure:
        verdict = "p1_flag"
    else:
        verdict = "pass"

    return QualityReport(
        item_id=str(item.id),
        checks=tuple(results),
        verdict=verdict,
        flags=tuple(flags),
    )


def phase3_foundation_checks() -> tuple[QualityCheck, ...]:
    """Return the foundation-grade check sequence.

    The follow-up slice extends this with adversarial, PII, dup,
    acoustic, and rubric-version checks. The order matches
    `phase3_design.md §5.1` (cheapest first; expensive LLM call last).
    """
    return (
        LicenseCompatibleCheck(),
        LengthBalancedDistractorsCheck(),
    )


__all__ = ["phase3_foundation_checks", "run_gate"]
