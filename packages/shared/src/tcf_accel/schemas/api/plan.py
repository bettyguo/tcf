"""`/v1/plan/*` — study plan read/regenerate.

Phase 4 implements the planner; Phase 2 freezes the wire shape.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.ids import StudyPlanId, UserId
from tcf_accel.schemas.item import Module

DrillType = Literal[
    # Phase 1–4 names (kept; planner emits the legacy name in `PlanBlock`,
    # the finer `DrillKind` in `Interaction.drill_kind`):
    "flashcard",
    "cloze",
    "mcq",
    "shadowing",
    "writing_short",
    "writing_long",
    "speaking_role",
    "speaking_mono",
    "mock_section",
    # Phase 5 additions (`phase5_design.md §10.2`):
    "co_dictation",
    "co_accent",
    "co_gapfill",
    "co_lexical_alt",
    "ce_skim_scan",
    "ce_vocab_context",
    "ce_register_id",
    "ce_summary",
    "ee_rewrite",
    "ee_connector",
    "ee_error_correction",
    "ee_register_adjust",
    "eo_picture",
    "eo_spontaneous",
    "eo_roleplay",
    "eo_repair",
    "eo_text_alt",
]

# `DrillKind` is the finer-grained enumeration that lands in
# `Interaction.drill_kind`. It distinguishes the exact drill that
# produced the row (e.g., `co_mcq` vs `ce_mcq`, both surfaced as
# `DrillType="mcq"` in the plan). Phase 5 ships 21 implementable
# kinds; `mock_section` and `diagnostic_item` are reserved-name
# placeholders owned by Phase 6 and Phase 4 respectively.
#
# Stability promise (ADR-014-adjacent): names are additive-only.
# Removing or renaming a `DrillKind` value is a SCHEMA_VERSION bump.
DrillKind = Literal[
    # CO module
    "co_mcq",
    "co_dictation",
    "co_shadowing",
    "co_accent",
    "co_gapfill",
    "co_lexical_alt",  # accessibility alt; emits `module=CE`. ADR-029.
    # CE module
    "ce_mcq",
    "ce_skim_scan",
    "ce_vocab_context",
    "ce_register_id",
    "ce_summary",
    # EE module
    "ee_task",
    "ee_rewrite",
    "ee_connector",
    "ee_error_correction",
    "ee_register_adjust",
    # EO module
    "eo_task",
    "eo_picture",
    "eo_spontaneous",
    "eo_roleplay",
    "eo_repair",
    "eo_text_alt",  # accessibility alt; emits `module=EE`.
    # Cross-cutting / owned by other phases
    "mock_section",  # Phase 6
    "diagnostic_item",  # Phase 4 CAT
]


class PlanBlock(BaseModel):
    """One activity in a daily block — typically 5–30 minutes."""

    model_config = ConfigDict(extra="forbid")

    skill: Module
    minutes: int = Field(ge=1, le=240)
    drill_type: DrillType
    rationale: str = Field(
        min_length=1,
        description="One-line explanation of why this block was scheduled (planner output).",
    )


class DailyBlock(BaseModel):
    """All blocks scheduled for a single calendar date."""

    model_config = ConfigDict(extra="forbid")

    date: date
    blocks: list[PlanBlock] = Field(default_factory=list)
    total_minutes: int = Field(ge=0, description="Sum of `block.minutes`; cached for the UI.")


class StudyPlanView(BaseModel):
    """The current rolling study plan."""

    model_config = ConfigDict(extra="forbid")

    id: StudyPlanId
    user_id: UserId
    generated_at: datetime
    horizon_days: int = Field(ge=1, le=365)
    daily_blocks: list[DailyBlock] = Field(default_factory=list)
    rationale: str = Field(
        min_length=1,
        description="Plan-level explanation of why this plan was generated.",
    )


__all__ = ["DailyBlock", "DrillKind", "DrillType", "PlanBlock", "StudyPlanView"]
