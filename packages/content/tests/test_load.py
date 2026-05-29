"""Tests for `tcf_accel_content.load`: the BankWriter contract and orchestrator."""

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
from tcf_accel_content.load import (
    BankWriter,
    InMemoryBankWriter,
    LoadOutcome,
    load_candidate,
)
from tcf_accel_content.quality.gate import phase3_foundation_checks
from tcf_accel_content.types import CandidateItem, QualityCheckResult, SynthesisTrace


@dataclass(frozen=True)
class _StubCheck:
    name: str
    severity: Literal["P0", "P1"]
    passed: bool

    def __call__(self, item: Item) -> QualityCheckResult:
        return QualityCheckResult(
            name=self.name, passed=self.passed,
            severity=self.severity, detail="stub",
        )


def _candidate(license: str = "CC0-1.0") -> CandidateItem:
    item = Item(
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
            source="x", source_id=str(uuid4()),
            license=license,
            ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )
    trace = SynthesisTrace(
        model="test", prompt_hash="0" * 64, response_hash="1" * 64,
        latency_ms=0.0, tokens_in=0, tokens_out=0,
    )
    return CandidateItem(item=item, trace=trace)


# ─── BankWriter / InMemoryBankWriter ───────────────────────────


def test_inmemory_writer_satisfies_protocol() -> None:
    assert isinstance(InMemoryBankWriter(), BankWriter)


def test_inmemory_write_new_item_returns_true() -> None:
    w = InMemoryBankWriter()
    assert w.write(_candidate().item) is True
    assert w.count() == 1


def test_inmemory_write_duplicate_returns_false() -> None:
    w = InMemoryBankWriter()
    candidate = _candidate()
    assert w.write(candidate.item) is True
    # Same id again — ON CONFLICT DO NOTHING semantic.
    assert w.write(candidate.item) is False
    assert w.count() == 1


def test_inmemory_get_returns_stored_item() -> None:
    w = InMemoryBankWriter()
    candidate = _candidate()
    w.write(candidate.item)
    assert w.get(candidate.item.id) == candidate.item


def test_inmemory_all_items_returns_insertion_order() -> None:
    w = InMemoryBankWriter()
    items = [_candidate().item for _ in range(3)]
    for it in items:
        w.write(it)
    assert w.all_items() == items


# ─── load_candidate orchestration ──────────────────────────────


def test_load_passes_item_through_to_writer() -> None:
    w = InMemoryBankWriter()
    candidate = _candidate()
    outcome = load_candidate(
        candidate, w,
        checks=phase3_foundation_checks(),
    )
    assert outcome.persisted is True
    assert outcome.reason == "wrote"
    assert outcome.report.verdict == "pass"
    assert w.count() == 1


def test_load_rejects_p0_failure_without_writing() -> None:
    w = InMemoryBankWriter()
    outcome = load_candidate(
        _candidate(license="proprietary"),
        w,
        checks=phase3_foundation_checks(),
    )
    assert outcome.persisted is False
    assert outcome.reason == "rejected_p0"
    assert outcome.report.verdict == "reject"
    assert w.count() == 0


def test_load_flags_p1_and_persists_with_needs_review_flag() -> None:
    w = InMemoryBankWriter()
    candidate = _candidate()
    outcome = load_candidate(
        candidate, w,
        checks=[_StubCheck(name="some_p1", severity="P1", passed=False)],
    )
    assert outcome.persisted is True
    assert outcome.reason == "wrote"
    assert outcome.report.verdict == "p1_flag"
    stored = w.get(candidate.item.id)
    assert stored is not None
    assert QualityFlag.NEEDS_HUMAN_REVIEW in stored.quality_flags


def test_load_can_skip_p1_flagged_items_when_caller_opts_out() -> None:
    w = InMemoryBankWriter()
    outcome = load_candidate(
        _candidate(), w,
        checks=[_StubCheck(name="some_p1", severity="P1", passed=False)],
        accept_p1_flag=False,
    )
    assert outcome.persisted is False
    assert outcome.reason == "flagged_p1_skipped"
    assert w.count() == 0


def test_load_is_idempotent_on_re_call_with_same_candidate() -> None:
    w = InMemoryBankWriter()
    candidate = _candidate()
    first = load_candidate(
        candidate, w, checks=phase3_foundation_checks(),
    )
    second = load_candidate(
        candidate, w, checks=phase3_foundation_checks(),
    )
    assert first.reason == "wrote"
    assert second.reason == "already_present"
    assert second.persisted is False
    assert w.count() == 1


def test_load_does_not_mutate_original_candidate_item() -> None:
    """`_attach_flags` returns a model_copy; the candidate is unchanged."""
    candidate = _candidate()
    before = candidate.item.model_dump()
    load_candidate(
        candidate, InMemoryBankWriter(),
        checks=[_StubCheck(name="p1", severity="P1", passed=False)],
    )
    assert candidate.item.model_dump() == before


def test_load_outcome_is_frozen_dataclass() -> None:
    outcome = load_candidate(
        _candidate(), InMemoryBankWriter(),
        checks=phase3_foundation_checks(),
    )
    assert isinstance(outcome, LoadOutcome)
    # Frozen dataclasses raise on field assignment.
    try:
        outcome.persisted = False  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("LoadOutcome should be frozen")
