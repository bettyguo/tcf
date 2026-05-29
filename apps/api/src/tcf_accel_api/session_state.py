"""In-process practice-session store + persistent dismissal log.

`phase5_design.md §13` carves persistence into three layers:

- The `sessions` and `interactions` tables (Postgres). Phase 9 deploy
  work wires real DB sessions through the routes; until then the
  in-process store below carries practice-session state across
  requests within a single process.
- `study_plans` (Postgres). Same posture as sessions — Phase 9.
- The **dismissal log** at `data/dismissal_log.jsonl`. This *is*
  persisted by Phase 5 because it is the per-operator privacy record
  ADR-017 commits to keeping local-only. The log is gitignored (Phase
  1 I5) and never crosses a network boundary.

The dismissal log path is overridable via the `TCF_ACCEL_DATA_DIR`
env var so tests can write to a tmp dir; production reads/writes
under `<repo>/data/`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Final
from uuid import UUID

from tcf_accel.ids import SessionId, UserId
from tcf_accel.schemas.api.plan import DrillKind, DrillType
from tcf_accel.schemas.api.session import DismissalLogEntry
from tcf_accel.schemas.item import Module
from tcf_accel_sla.session import SessionRecord, iso_week

_DATA_DIR_ENV: Final[str] = "TCF_ACCEL_DATA_DIR"
_DISMISSAL_LOG_FILENAME: Final[str] = "dismissal_log.jsonl"

# Repository-root data dir. Tests override via TCF_ACCEL_DATA_DIR; the
# operator's deployment uses the default, which points at the
# (gitignored) `data/` directory at the repo root.
_DEFAULT_DATA_DIR: Final[Path] = Path(__file__).resolve().parents[4] / "data"


def _data_dir() -> Path:
    """Return the data directory (env-overridable for tests)."""
    override = os.environ.get(_DATA_DIR_ENV)
    return Path(override) if override else _DEFAULT_DATA_DIR


def _dismissal_log_path() -> Path:
    """Return the dismissal-log file path (ADR-017 — local-only)."""
    return _data_dir() / _DISMISSAL_LOG_FILENAME


@dataclass
class PracticeSession:
    """One in-flight or finished practice session."""

    id: SessionId
    user_id: UserId
    module: Module
    drill_type: DrillType
    drill_kind: DrillKind
    posterior_skill: Module  # which posterior this drill updates (CE for co_lexical_alt)
    target_minutes: int
    exam_shape: bool
    started_at: datetime
    queue: list[UUID]  # remaining item ids
    start_posterior_mean: float  # snapshot for the finish-summary delta
    cursor: int = 0  # index of the next item to serve
    items_seen: int = 0
    items_correct: int = 0
    paused_at: datetime | None = None
    finished_at: datetime | None = None
    # item_id currently awaiting an answer (set by /next, cleared by /answer)
    pending_item_id: UUID | None = None
    # idempotency: item_ids already answered in this session
    answered: set[UUID] = field(default_factory=set)


@dataclass
class SessionStore:
    """All practice-session state for one user, in one process."""

    sessions: dict[SessionId, PracticeSession] = field(default_factory=dict)
    # ISO-week designators the user has dismissed the exam-shape floor for.
    dismissals: list[str] = field(default_factory=list)
    # Has the on-disk dismissal log been loaded into this store yet?
    # Lazy to keep test isolation cheap (a test can monkey-patch the
    # env var, then the first `dismissed_this_week`/`record_dismissal`
    # call triggers a one-time disk read).
    _dismissals_loaded: bool = False


_STORE: Final[dict[UserId, SessionStore]] = {}
_LOCK: Final[Lock] = Lock()


# ─── Dismissal-log file I/O ────────────────────────────────────


def _append_dismissal_to_disk(entry: DismissalLogEntry) -> None:
    """Append one entry to the local dismissal log (ADR-017).

    Creates the parent directory if missing. The on-disk shape is
    `DismissalLogEntry.model_dump_json()` per line — same Pydantic
    contract as the wire schema, so a tail of the file is also a
    valid sequence of NDJSON records the audit can replay.

    Failures during write are *non-fatal* — the in-process record is
    already in the cache, and a missing audit row is preferable to a
    failed dismissal (the learner's flow is the priority; the file is
    an operator-side audit, not a transaction log).
    """
    path = _dismissal_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(entry.model_dump_json())
            fh.write("\n")
    except OSError:
        # Operator-side audit; a write failure must not break the request.
        # The in-memory cache still reflects the dismissal.
        return


def _load_dismissals_into_store(user_id: UserId, store: SessionStore) -> None:
    """Hydrate `store.dismissals` from the on-disk log on first access."""
    if store._dismissals_loaded:
        return
    store._dismissals_loaded = True
    path = _dismissal_log_path()
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    weeks: set[str] = set(store.dismissals)
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Only entries for THIS user contribute; the file may contain
        # multi-user records when a single operator hosts several
        # learners (Phase 5 single-user default still produces a clean
        # log).
        if row.get("user_id") != str(user_id):
            continue
        week = row.get("week_iso")
        if isinstance(week, str) and week:
            weeks.add(week)
    store.dismissals = sorted(weeks)


# ─── Public store API ──────────────────────────────────────────


def get_session_store(user_id: UserId) -> SessionStore:
    """Return (or lazily create) the practice-session store for a user."""
    with _LOCK:
        store = _STORE.get(user_id)
        if store is None:
            store = SessionStore()
            _STORE[user_id] = store
        return store


def get_session(user_id: UserId, session_id: UUID) -> PracticeSession | None:
    """Return the user's named practice session, or None."""
    return get_session_store(user_id).sessions.get(SessionId(session_id))


def put_session(user_id: UserId, session: PracticeSession) -> None:
    """Register a practice session under the user."""
    get_session_store(user_id).sessions[session.id] = session


def session_records(user_id: UserId) -> list[SessionRecord]:
    """Project the user's sessions onto the exam-shape-floor record shape."""
    store = get_session_store(user_id)
    return [
        SessionRecord(
            finished_at=s.finished_at,
            exam_shape=s.exam_shape,
            target_minutes=s.target_minutes,
        )
        for s in store.sessions.values()
    ]


def record_dismissal(user_id: UserId, *, now: datetime) -> str:
    """Record an exam-shape-floor dismissal for the current ISO week.

    Updates the in-process cache AND appends a typed
    `DismissalLogEntry` line to `data/dismissal_log.jsonl`. The file
    is the operator's local audit record (ADR-017); it is never
    replicated to a cloud backend. Two calls in the same week are
    idempotent — the in-process cache de-dupes; the file may have a
    duplicate line, which the loader collapses on read.

    Returns the ISO-week designator that was dismissed.
    """
    week = iso_week(now)
    store = get_session_store(user_id)
    _load_dismissals_into_store(user_id, store)
    if week in store.dismissals:
        return week  # already recorded this week — skip the disk write
    store.dismissals.append(week)
    _append_dismissal_to_disk(
        DismissalLogEntry(user_id=user_id, dismissed_at=now, week_iso=week),
    )
    return week


def dismissed_this_week(user_id: UserId, *, now: datetime) -> bool:
    """True iff the user dismissed the floor for the current ISO week."""
    store = get_session_store(user_id)
    _load_dismissals_into_store(user_id, store)
    return iso_week(now) in store.dismissals


def reset_all() -> None:
    """Drop all in-process practice-session state. Used by tests.

    Does **not** truncate the on-disk dismissal log — that is an
    operator-owned audit file. Tests that need a clean log should
    point `TCF_ACCEL_DATA_DIR` at a tmp path before importing the
    module's callers.
    """
    with _LOCK:
        _STORE.clear()


__all__ = [
    "PracticeSession",
    "SessionStore",
    "dismissed_this_week",
    "get_session",
    "get_session_store",
    "put_session",
    "record_dismissal",
    "reset_all",
    "session_records",
]
