"""In-process mock-exam state + journal.

Mirrors `session_state.py`. The store keys mocks by `MockExamId` and
indexes by user. Phase 9 swaps for Redis (live state) + Postgres
(journal); the wire shape does not change.

Forfeit detection (tab-blur, process abort) is the route layer's
responsibility — this module records the transition that the route
decides to apply.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Final
from uuid import UUID

from tcf_accel.ids import ItemId, MockExamId, UserId
from tcf_accel.schemas.item import Module
from tcf_accel.schemas.scoring import SkillCode

from tcf_accel_sla.mock_exam import (
    MockExamMode,
    MockJournalEntry,
    MockState,
)
from tcf_accel_sla.mock_exam.cadence import MockExamSummary
from tcf_accel_sla.mock_exam.scorer import (
    ItemOutcome,
    MockSkillScore,
    RubricOutcome,
)
from tcf_accel_sla.mock_exam.selector import PooledMockItem


@dataclass
class MockExam:
    """One mock exam's full state, in-process."""

    id: MockExamId
    user_id: UserId
    mode: MockExamMode
    state: MockState
    started_at: datetime
    items_by_module: dict[Module, list[PooledMockItem]] = field(default_factory=dict)
    outcomes: dict[ItemId, ItemOutcome | RubricOutcome] = field(default_factory=dict)
    co_plays: dict[ItemId, int] = field(default_factory=dict)
    current_module: Module | None = None
    seconds_remaining_in_module: int = 0
    module_started_at: datetime | None = None
    state_entered_at: datetime | None = None
    journal: list[MockJournalEntry] = field(default_factory=list)
    skill_scores: dict[SkillCode, MockSkillScore] | None = None
    overall_nclc: int | None = None
    overall_confident: bool = False
    bottleneck_skill: SkillCode | None = None
    divergence_alerts: list[str] = field(default_factory=list)
    finished_at: datetime | None = None
    scored_at: datetime | None = None
    selector_warnings: list[str] = field(default_factory=list)


@dataclass
class MockStore:
    """All mock-exam state for one user."""

    mocks: dict[MockExamId, MockExam] = field(default_factory=dict)
    first_canonical_at: datetime | None = None


_STORE: Final[dict[UserId, MockStore]] = {}
_LOCK: Final[Lock] = Lock()


def get_mock_store(user_id: UserId) -> MockStore:
    """Return (or lazily create) the mock-exam store for a user."""
    with _LOCK:
        store = _STORE.get(user_id)
        if store is None:
            store = MockStore()
            _STORE[user_id] = store
        return store


def get_mock(user_id: UserId, mock_id: UUID) -> MockExam | None:
    """Return the named mock for the user, or None."""
    return get_mock_store(user_id).mocks.get(MockExamId(mock_id))


def put_mock(user_id: UserId, mock: MockExam) -> None:
    """Register a mock under the user."""
    store = get_mock_store(user_id)
    store.mocks[mock.id] = mock
    if mock.mode == "canonical" and store.first_canonical_at is None:
        store.first_canonical_at = mock.started_at


def history(user_id: UserId) -> Iterable[MockExamSummary]:
    """Project the user's mocks into cadence-friendly summaries."""
    store = get_mock_store(user_id)
    for m in store.mocks.values():
        yield MockExamSummary(
            started_at=m.started_at,
            mode=m.mode,
            forfeited=(m.state == MockState.FORFEITED),
        )


def reset_all() -> None:
    """Drop all in-process mock-exam state (test helper)."""
    with _LOCK:
        _STORE.clear()


def journal(mock: MockExam, *, at: datetime, to_state: MockState, reason: str) -> None:
    """Append one journal entry and update the bookkeeping fields."""
    entered = mock.state_entered_at or mock.started_at
    elapsed = (at - entered).total_seconds()
    mock.journal.append(
        MockJournalEntry(
            mock_id=mock.id,
            at=at,
            from_state=mock.state,
            to_state=to_state,
            reason=reason,
            elapsed_s_in_state=elapsed,
        ),
    )
    mock.state = to_state
    mock.state_entered_at = at


__all__ = [
    "MockExam",
    "MockStore",
    "get_mock",
    "get_mock_store",
    "history",
    "journal",
    "put_mock",
    "reset_all",
]
