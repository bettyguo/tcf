"""`/v1/session/*` — practice session lifecycle.

Phase 5 implements; Phase 2 freezes the wire shape.

Phase 5 additive: `DismissalLogEntry` records exam-shape-floor
dismissals (ADR-028). The dismissal log is local-only (per ADR-017);
it is never replicated to a cloud backend.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.ids import ItemId, SessionId, UserId
from tcf_accel.schemas.api.plan import DrillType
from tcf_accel.schemas.item import Item, Module


class SessionStart(BaseModel):
    """Body of `POST /v1/session/start`."""

    model_config = ConfigDict(extra="forbid")

    module: Module
    drill_type: DrillType
    target_minutes: int = Field(
        ge=1, le=240, description="Soft target; the planner may exceed for due reviews."
    )


class SessionState(BaseModel):
    """The session lifecycle envelope."""

    model_config = ConfigDict(extra="forbid")

    id: SessionId
    user_id: UserId
    module: Module
    drill_type: DrillType
    target_minutes: int = Field(ge=1, le=240)
    started_at: datetime
    finished_at: datetime | None = None
    items_seen: int = Field(ge=0)
    items_correct: int = Field(ge=0)


class SessionItem(BaseModel):
    """The next item to render, with any session-scoped hints."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    item: Item
    is_review: bool = Field(
        description="True if the item is due for review (FSRS); False for new items.",
    )
    expected_rt_ms: int | None = Field(
        default=None,
        ge=0,
        description="Planner's expected response time; used by the UI for a soft timer.",
    )


class SessionAnswer(BaseModel):
    """Body of `POST /v1/session/{id}/answer`."""

    model_config = ConfigDict(extra="forbid")

    item_id: ItemId
    response: dict[str, object] = Field(
        description="Shape depends on the item's module (MCQ option id, text, audio URI, etc).",
    )
    rt_ms: int = Field(ge=0)
    rating: int | None = Field(
        default=None,
        ge=1,
        le=4,
        description="FSRS self-rating (1=again, 2=hard, 3=good, 4=easy). Optional; the scheduler can infer from correctness for MCQs.",
    )


class SkillDelta(BaseModel):
    """Posterior shift in a single skill across the session."""

    model_config = ConfigDict(extra="forbid")

    skill: Module
    before: float = Field(ge=1, le=12)
    after: float = Field(ge=1, le=12)
    delta: float = Field(description="Signed shift; positive = improvement.")


class SessionSummary(BaseModel):
    """Returned by `POST /v1/session/{id}/finish`."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    finished_at: datetime
    items_seen: int = Field(ge=0)
    items_correct: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    deltas: list[SkillDelta] = Field(default_factory=list)
    cards_due_next_24h: int = Field(ge=0)
    plan_regenerated: bool = Field(
        description="True if the posterior shift crossed the threshold (ADR-0012) and the plan was rebuilt.",
    )


class DismissalLogEntry(BaseModel):
    """One record of an exam-shape floor dismissal (ADR-028).

    Stored local-only at `data/dismissal_log.jsonl` (gitignored per
    Phase 1 I5). 90-day retention; the daily housekeeper truncates
    older entries.

    The dismissal is per-ISO-week: a single dismissal moves the
    learner past the floor for the calendar week named in
    `week_iso`. `audit-exam-shape` flags users with ≥ 4 dismissals
    in any rolling 8-week window; the doctrine remains, the audit
    flags the divergence.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: UserId
    dismissed_at: datetime
    week_iso: str = Field(
        min_length=8,
        max_length=10,
        description="ISO week designator, e.g. '2026-W22'.",
    )
    reason: str | None = Field(
        default=None,
        max_length=240,
        description="Optional free-text reason; logged for the operator's audit only.",
    )


__all__ = [
    "DismissalLogEntry",
    "SessionAnswer",
    "SessionItem",
    "SessionStart",
    "SessionState",
    "SessionSummary",
    "SkillDelta",
]
