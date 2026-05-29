"""`/v1/diagnostic/*` — initial-assessment flow.

Phase 5 implements; Phase 2 freezes the wire shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.ids import ItemId, SessionId, UserId
from tcf_accel.schemas.item import CefrLevel, Module
from tcf_accel.schemas.scoring import NCLCEstimate


class DiagnosticState(BaseModel):
    """Mid-flight state of the adaptive diagnostic session."""

    model_config = ConfigDict(extra="forbid")

    id: SessionId
    user_id: UserId
    started_at: datetime
    finished_at: datetime | None = None
    current_module: Module | None = Field(
        default=None,
        description="The module the next item will be drawn from; None when finished.",
    )
    completed_modules: list[Module] = Field(default_factory=list)
    items_seen: int = Field(ge=0)
    next_item_id: ItemId | None = Field(
        default=None,
        description="Pre-fetched next item; the client renders this when the user advances.",
    )
    estimates_in_progress: dict[Module, float] = Field(
        default_factory=dict,
        description="Running posterior mean per skill (continuous NCLC). UI shows these only with a confidence indicator.",
    )


class DiagnosticAnswer(BaseModel):
    """The candidate's response to a single diagnostic item."""

    model_config = ConfigDict(extra="forbid")

    item_id: ItemId
    response: dict[str, object] = Field(
        description="MCQ option id, free text, audio URI, etc. Shape depends on the item's module.",
    )
    rt_ms: int = Field(ge=0, description="Response time in milliseconds.")


class SkillLevel(BaseModel):
    """One skill's diagnostic result."""

    model_config = ConfigDict(extra="forbid")

    skill: Module
    estimate: NCLCEstimate
    cefr_band: CefrLevel = Field(
        description="Best-fit CEFR level for the posterior mean (advisory; NCLC is canonical).",
    )


class DiagnosticReport(BaseModel):
    """Final diagnostic report — returned by `POST /v1/diagnostic/{id}/finish`."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    user_id: UserId
    completed_at: datetime
    per_skill: list[SkillLevel] = Field(min_length=1)
    bottleneck_skill: Module = Field(
        description="The lowest NCLC skill; the planner will weight this skill first.",
    )
    plan_id: str | None = Field(
        default=None,
        description="Id of the StudyPlan generated from this diagnostic, if any.",
    )
    confidence_summary: Literal["high", "partial", "exploratory"] = Field(
        description=(
            "high: all four skills `confident=True`. partial: some skills confident. "
            "exploratory: no skill confident — user should do another session before booking the exam."
        ),
    )


__all__ = [
    "DiagnosticAnswer",
    "DiagnosticReport",
    "DiagnosticState",
    "SkillLevel",
]
