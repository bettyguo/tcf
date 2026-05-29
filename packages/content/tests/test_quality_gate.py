"""Tests for the gate composer (`tcf_accel_content.quality.gate`)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from tcf_accel.ids import ItemId
from tcf_accel.schemas import (
    MCQ,
    CEContent,
    Item,
    MCQOption,
    Provenance,
    QualityFlag,
)
from tcf_accel_content.quality.gate import phase3_foundation_checks, run_gate
from tcf_accel_content.types import QualityCheckResult


@dataclass(frozen=True)
class _StubCheck:
    name: str
    severity: Literal["P0", "P1"]
    passed: bool

    def __call__(self, item: Item) -> QualityCheckResult:
        return QualityCheckResult(
            name=self.name,
            passed=self.passed,
            severity=self.severity,
            detail="stub",
        )


def _ce_item(license: str = "CC0-1.0") -> Item:
    return Item(
        id=ItemId(uuid4()),
        module="CE",
        cefr_level="B2",
        content=CEContent(
            passage=" ".join(["lorem"] * 30),
            genre="news",
            word_count=30,
            questions=[
                MCQ(
                    id="q1",
                    prompt="?",
                    options=[
                        MCQOption(id="a", text="aa bb cc dd"),
                        MCQOption(id="b", text="ee ff gg hh"),
                        MCQOption(id="c", text="ii jj kk ll"),
                        MCQOption(id="d", text="mm nn oo pp"),
                    ],
                    correct_option_id="a",
                ),
            ],
        ),
        provenance=Provenance(
            source="x", source_id="1", license=license,
            ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )


# ─── verdict logic ─────────────────────────────────────────────


def test_all_passing_yields_pass() -> None:
    report = run_gate(_ce_item(), [
        _StubCheck(name="c1", severity="P0", passed=True),
        _StubCheck(name="c2", severity="P1", passed=True),
    ])
    assert report.verdict == "pass"
    assert report.flags == ()
    assert len(report.checks) == 2


def test_p0_failure_yields_reject() -> None:
    report = run_gate(_ce_item(), [
        _StubCheck(name="c1", severity="P0", passed=False),
        _StubCheck(name="c2", severity="P1", passed=True),
    ])
    assert report.verdict == "reject"


def test_p1_failure_yields_flag_with_needs_human_review() -> None:
    report = run_gate(_ce_item(), [
        _StubCheck(name="c1", severity="P0", passed=True),
        _StubCheck(name="c2", severity="P1", passed=False),
    ])
    assert report.verdict == "p1_flag"
    assert QualityFlag.NEEDS_HUMAN_REVIEW.value in report.flags


def test_p0_failure_dominates_p1_failure() -> None:
    report = run_gate(_ce_item(), [
        _StubCheck(name="c1", severity="P1", passed=False),
        _StubCheck(name="c2", severity="P0", passed=False),
    ])
    assert report.verdict == "reject"
    # P1 failure still emits the flag for audit completeness; it just
    # does not override the P0-driven reject verdict.
    assert QualityFlag.NEEDS_HUMAN_REVIEW.value in report.flags


def test_every_check_runs_even_after_p0_failure() -> None:
    report = run_gate(_ce_item(), [
        _StubCheck(name="early_p0", severity="P0", passed=False),
        _StubCheck(name="later_p1", severity="P1", passed=False),
        _StubCheck(name="latest_p0", severity="P0", passed=True),
    ])
    assert [r.name for r in report.checks] == ["early_p0", "later_p1", "latest_p0"]


def test_flag_is_emitted_only_once_for_multiple_p1_failures() -> None:
    report = run_gate(_ce_item(), [
        _StubCheck(name="c1", severity="P1", passed=False),
        _StubCheck(name="c2", severity="P1", passed=False),
    ])
    assert report.flags == (QualityFlag.NEEDS_HUMAN_REVIEW.value,)


def test_item_id_propagates_to_report() -> None:
    item = _ce_item()
    report = run_gate(item, [])
    assert report.item_id == str(item.id)


# ─── default foundation checks ─────────────────────────────────


def test_phase3_foundation_checks_returns_expected_pair() -> None:
    checks = phase3_foundation_checks()
    names = {c.name for c in checks}
    assert names == {"license_compatible", "length_balanced_distractors"}


def test_foundation_checks_pass_on_balanced_ce_item() -> None:
    report = run_gate(_ce_item(), phase3_foundation_checks())
    assert report.verdict == "pass"


def test_foundation_checks_reject_on_bad_license() -> None:
    report = run_gate(_ce_item(license="proprietary"), phase3_foundation_checks())
    assert report.verdict == "reject"
