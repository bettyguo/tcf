"""`/v1/insights/*` — derived views over the learner's history.

Phase 8 implements; Phase 2 freezes the wire shape.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.schemas.item import Module
from tcf_accel.schemas.scoring import NCLCEstimate

ReadinessLight = Literal["red", "yellow", "green"]


class NCLCTrajectoryPoint(BaseModel):
    """One point on the historical + forecast trajectory."""

    model_config = ConfigDict(extra="forbid")

    at: datetime
    skill: Module
    posterior_mean: float = Field(ge=1, le=12)
    ci_low: int = Field(ge=1, le=12)
    ci_high: int = Field(ge=1, le=12)
    is_forecast: bool = Field(
        description="True for points that come from the planner forecast (after now()); False for observed history.",
    )


class NCLCTrajectory(BaseModel):
    """Time series of estimates per skill, with forecast extension."""

    model_config = ConfigDict(extra="forbid")

    horizon_end: date
    points: list[NCLCTrajectoryPoint] = Field(default_factory=list)


class WeakPoint(BaseModel):
    """One identified error pattern, derived from interactions + rubrics."""

    model_config = ConfigDict(extra="forbid")

    skill: Module
    pattern: str = Field(
        min_length=1,
        description="Short human-readable label, e.g. 'subjunctive after que' or 'fr-CA accent confusable'.",
    )
    occurrences: int = Field(ge=1)
    last_seen: datetime
    severity: Literal["low", "medium", "high"]
    suggested_drill: str | None = Field(
        default=None,
        description="Pointer to a drill type the planner can schedule (DrillType enum value).",
    )


class Readiness(BaseModel):
    """The traffic-light 'are you ready to book the exam?' answer.

    Per R-004 + Phase 9 launch gate: 🟢 requires two consecutive
    canonical-mock greens *and* `confident=True` on all four skills.
    The Phase 8 UI surfaces this as the headline.
    """

    model_config = ConfigDict(extra="forbid")

    light: ReadinessLight
    per_skill: list[NCLCEstimate] = Field(min_length=1)
    reason: str = Field(
        min_length=1,
        description="One-paragraph explanation of why the light is its color.",
    )
    last_canonical_mock_at: datetime | None = None
    canonical_mock_streak_green: int = Field(
        ge=0,
        description="Consecutive canonical-mock greens; ≥ 2 is one prerequisite for overall green.",
    )


__all__ = [
    "NCLCTrajectory",
    "NCLCTrajectoryPoint",
    "Readiness",
    "ReadinessLight",
    "WeakPoint",
]
