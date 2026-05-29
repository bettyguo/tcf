"""`/v1/mock-exam/*` — full 2h47 mock-exam orchestration.

Phase 6 implements; Phase 2 freezes the wire shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.ids import ItemId, MockExamId, UserId
from tcf_accel.schemas.item import Module
from tcf_accel.schemas.scoring import NCLCEstimate

MockExamMode = Literal["canonical", "training"]
MockExamStatus = Literal["in_progress", "submitted", "scored"]


class PerModuleScore(BaseModel):
    """Raw + scaled score for one module."""

    model_config = ConfigDict(extra="forbid")

    module: Module
    raw_score: float = Field(ge=0)
    max_score: float = Field(ge=0)
    estimate: NCLCEstimate


class MockExamState(BaseModel):
    """The mock-exam's lifecycle envelope."""

    model_config = ConfigDict(extra="forbid")

    id: MockExamId
    user_id: UserId
    mode: MockExamMode = Field(
        description="canonical: locks shape to FEI spec; training: relaxed for diagnostic practice.",
    )
    status: MockExamStatus
    started_at: datetime
    finished_at: datetime | None = None
    current_module: Module | None = None
    current_item_id: ItemId | None = None
    seconds_remaining_in_module: int | None = Field(
        default=None,
        ge=0,
        description="Soft countdown the UI uses; the server is the source of truth for actual locking.",
    )


class MockExamReport(BaseModel):
    """Returned by `GET /v1/mock-exam/{id}/report`."""

    model_config = ConfigDict(extra="forbid")

    id: MockExamId
    user_id: UserId
    completed_at: datetime
    per_module: list[PerModuleScore] = Field(min_length=1)
    overall_nclc: int = Field(
        ge=1,
        le=12,
        description="Composite NCLC (lowest skill per TCF Canada equivalence).",
    )
    overall_confident: bool
    bottleneck_skill: Module
    item_log_uri: str = Field(
        description="URI to the full per-item log (JSONL); fetched separately to keep this response small.",
    )


class MockExamStart(BaseModel):
    """Body of `POST /v1/mock-exam/start` (Phase 6 additive)."""

    model_config = ConfigDict(extra="forbid")

    mode: MockExamMode = "canonical"
    force: bool = Field(
        default=False,
        description="Override the cadence cap; logged at WARN for audit.",
    )


class MockExamAnswer(BaseModel):
    """Body of `POST /v1/mock-exam/{id}/answer` (Phase 6 additive)."""

    model_config = ConfigDict(extra="forbid")

    item_id: ItemId
    module: Module
    kind: Literal["mcq", "rubric"]
    selected_option_id: str | None = Field(
        default=None,
        max_length=8,
        description="Required when kind=mcq.",
    )
    rubric_total_20: float | None = Field(
        default=None,
        ge=0,
        le=20,
        description="Required when kind=rubric.",
    )
    task_number: int | None = Field(
        default=None,
        ge=1,
        le=3,
        description="Required when kind=rubric (EE/EO 1, 2, 3).",
    )
    rt_ms: int = Field(default=0, ge=0)


class MockExamCoPlay(BaseModel):
    """Body of `POST /v1/mock-exam/{id}/co-play` (Phase 6 additive)."""

    model_config = ConfigDict(extra="forbid")

    item_id: ItemId


class MockExamTabBlur(BaseModel):
    """Body of `POST /v1/mock-exam/{id}/tab-blur` (Phase 6 additive)."""

    model_config = ConfigDict(extra="forbid")

    duration_ms: int = Field(ge=0)


__all__ = [
    "MockExamAnswer",
    "MockExamCoPlay",
    "MockExamMode",
    "MockExamReport",
    "MockExamStart",
    "MockExamState",
    "MockExamStatus",
    "MockExamTabBlur",
    "PerModuleScore",
]
