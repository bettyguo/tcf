"""Bank loader: the only stage that persists items.

Per `phase3_design.md §1.1`, all upstream stages cache to `data/cache/`;
the bank loader is the one stage that touches the actual `items`
table. To keep that contract testable without a live Postgres, the
loader is parameterized on a `BankWriter` protocol — production wires
a SQLAlchemy-backed writer (Phase 3 follow-up); tests use the
`InMemoryBankWriter` shipped here.

The orchestrator `load_candidate` composes the gate + writer:

1. Run the quality gate on the candidate.
2. If the verdict is ``"reject"``: do nothing, return a ``LoadOutcome``
   carrying the report and ``persisted=False, reason="rejected_p0"``.
3. If the verdict is ``"p1_flag"``: attach the report's flags to
   ``item.quality_flags`` (so the row carries the audit signal) and
   call ``writer.write``. The writer's ``ON CONFLICT (id) DO NOTHING``
   semantic is what makes the loader idempotent across re-runs.
4. If the verdict is ``"pass"``: write as-is.

The deterministic ``Item.id`` (per `phase3_design.md §1.2`) is what
makes step (3)/(4) safe to call repeatedly: re-running the pipeline
against the same source asset produces the same id; the writer's
``write`` returns ``False`` for a duplicate so the loader reports
``reason="already_present"`` without raising.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

from tcf_accel.schemas import Item, QualityFlag

from tcf_accel_content.quality import QualityCheck
from tcf_accel_content.quality.gate import run_gate
from tcf_accel_content.types import CandidateItem, QualityReport

LoadReason = Literal[
    "wrote",
    "already_present",
    "rejected_p0",
    "flagged_p1_skipped",
]


@dataclass(frozen=True)
class LoadOutcome:
    """The result of attempting to load one candidate item.

    `persisted` is True iff the writer accepted the item. `reason`
    distinguishes the four cases the loader produces:

    - ``"wrote"``: writer accepted the item (newly inserted).
    - ``"already_present"``: writer reports the id already exists.
      Idempotency contract — re-running the pipeline against the
      same source converges to the same items.
    - ``"rejected_p0"``: gate verdict was ``"reject"``; writer not called.
    - ``"flagged_p1_skipped"``: gate verdict was ``"p1_flag"`` and the
      caller passed ``accept_p1_flag=False``; writer not called.
    """

    candidate: CandidateItem
    report: QualityReport
    persisted: bool
    reason: LoadReason


@runtime_checkable
class BankWriter(Protocol):
    """The single persistence surface for the loader.

    Implementations:

    - `InMemoryBankWriter` (this module) — for tests.
    - `PostgresBankWriter` (Phase 3 follow-up) — wraps SQLAlchemy + the
      Phase 2 `items` table, with ``ON CONFLICT (id) DO NOTHING``.

    The contract is small on purpose: the loader cares only about
    "did this write produce a new row?".
    """

    def write(self, item: Item) -> bool:
        """Persist `item`. Return True if newly written, False on conflict."""
        ...


@dataclass
class InMemoryBankWriter:
    """Dict-backed `BankWriter` for tests and dry-runs.

    Mirrors the ``INSERT ... ON CONFLICT (Item.id) DO NOTHING`` semantic
    of the production Postgres writer.

    Example:
        >>> w = InMemoryBankWriter()
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
        ...         questions=[MCQ(id="q", prompt="?",
        ...             options=[MCQOption(id="a", text="x"),
        ...                      MCQOption(id="b", text="y")],
        ...             correct_option_id="a")],
        ...     ),
        ...     provenance=Provenance(source="x", source_id="1",
        ...         license="CC0-1.0",
        ...         ingested_at=datetime(2026,1,1,tzinfo=UTC)),
        ... )
        >>> w.write(item)
        True
        >>> w.write(item)
        False
        >>> w.count()
        1

    Complexity: O(1) per write; O(1) per `count`.
    """

    _rows: dict[UUID, Item] = field(default_factory=dict)

    def write(self, item: Item) -> bool:
        """Insert if absent; return True iff a new row was written."""
        if item.id in self._rows:
            return False
        self._rows[item.id] = item
        return True

    def count(self) -> int:
        """Return the number of distinct items currently held."""
        return len(self._rows)

    def get(self, item_id: UUID) -> Item | None:
        """Look up an item by id, or None if absent."""
        return self._rows.get(item_id)

    def all_items(self) -> list[Item]:
        """Return a snapshot list of all items (insertion order)."""
        return list(self._rows.values())


def load_candidate(
    candidate: CandidateItem,
    writer: BankWriter,
    *,
    checks: Sequence[QualityCheck],
    accept_p1_flag: bool = True,
) -> LoadOutcome:
    """Run the gate and conditionally write `candidate.item` to the bank.

    Args:
        candidate: A `CandidateItem` produced by a synthesizer.
        writer: A `BankWriter`-conforming sink.
        checks: The gate checks to run; ordered cheapest-first by the
            caller.
        accept_p1_flag: When True (default), items with verdict
            ``"p1_flag"`` are persisted with `NEEDS_HUMAN_REVIEW` in
            `quality_flags`. When False, they are skipped (the operator
            wants only clean items in this run).

    Returns:
        A `LoadOutcome` carrying the candidate, the gate report, the
        persisted flag, and the structured `reason`.

    Complexity: O(gate cost) + O(1) writer call.
    """
    report = run_gate(candidate.item, checks)
    if report.verdict == "reject":
        return LoadOutcome(
            candidate=candidate, report=report,
            persisted=False, reason="rejected_p0",
        )
    if report.verdict == "p1_flag":
        if not accept_p1_flag:
            return LoadOutcome(
                candidate=candidate, report=report,
                persisted=False, reason="flagged_p1_skipped",
            )
        item_to_write = _attach_flags(candidate.item, report.flags)
    else:
        item_to_write = candidate.item

    newly_written = writer.write(item_to_write)
    return LoadOutcome(
        candidate=candidate, report=report,
        persisted=newly_written,
        reason="wrote" if newly_written else "already_present",
    )


def _attach_flags(item: Item, flag_values: tuple[str, ...]) -> Item:
    """Return a copy of `item` with `flag_values` merged into `quality_flags`.

    Unknown flag strings are silently ignored; only members of the
    `QualityFlag` enum are added (the schema rejects others).
    """
    existing = set(item.quality_flags)
    additions: list[QualityFlag] = []
    for raw in flag_values:
        try:
            flag = QualityFlag(raw)
        except ValueError:
            continue
        if flag not in existing:
            additions.append(flag)
            existing.add(flag)
    if not additions:
        return item
    return item.model_copy(
        update={"quality_flags": [*item.quality_flags, *additions]},
    )


__all__ = [
    "BankWriter",
    "InMemoryBankWriter",
    "LoadOutcome",
    "LoadReason",
    "load_candidate",
]
