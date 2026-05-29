"""Pydantic schemas — the frozen contract surface.

Phase 1 baseline: `Item`, `Score`, `NCLCEstimate`, `Provenance`,
`QualityFlag`, `ItemMetadata`, `ReviewStatus`, `Module`, `SkillCode`,
`SCHEMA_VERSION`.

Phase 2 additive narrowing + extensions:
- `ItemContent` narrowed to a discriminated union (`COContent | CEContent
  | EEContent | EOContent`); per-module shapes in
  `tcf_accel.schemas.content`.
- `WritingRubric`, `SpeakingRubric`, `ErrorAnnotation`, `Speaker`,
  `MCQ`, `MCQOption`.
- `/v1/` API request/response models in `tcf_accel.schemas.api.*`.

Consumers can `from tcf_accel.schemas import Item, COContent,
WritingRubric, ErrorEnvelope, SCHEMA_VERSION` etc.
"""

from __future__ import annotations

# Phase 2 API surface --------------------------------------------
from tcf_accel.schemas.api import (
    AccessibilityProfile,
    DailyBlock,
    DiagnosticAnswer,
    DiagnosticReport,
    DiagnosticState,
    DismissalLogEntry,
    DrillKind,
    ErrorEnvelope,
    LoginRequest,
    MeProfile,
    MockExamReport,
    MockExamState,
    NCLCTrajectory,
    PlanBlock,
    Readiness,
    RefreshRequest,
    SessionAnswer,
    SessionItem,
    SessionStart,
    SessionState,
    SessionSummary,
    SignupRequest,
    StudyPlanView,
    SubmissionView,
    TokenPair,
    UpdateMeRequest,
    WeakPoint,
)

# Phase 1 surface ------------------------------------------------
from tcf_accel.schemas.common import (
    ItemMetadata,
    Provenance,
    QualityFlag,
    ReviewStatus,
)

# Phase 2 content variants ---------------------------------------
from tcf_accel.schemas.content import (
    MCQ,
    CEContent,
    COContent,
    EEContent,
    EOContent,
    ErrorAnnotation,
    MCQOption,
    Speaker,
)
from tcf_accel.schemas.interaction import Interaction
from tcf_accel.schemas.item import CefrLevel, Item, ItemContent, Module
from tcf_accel.schemas.pronunciation import (
    PronunciationDisplayLabel,
    PronunciationProsody,
    PronunciationSignal,
)
from tcf_accel.schemas.scoring import (
    NCLCEstimate,
    Score,
    SkillCode,
    SpeakingRubric,
    WritingRubric,
)
from tcf_accel.schemas.version import SCHEMA_VERSION

__all__ = [
    "SCHEMA_VERSION",
    # Phase 1
    "CefrLevel",
    "Interaction",
    "Item",
    "ItemContent",
    "ItemMetadata",
    "Module",
    "NCLCEstimate",
    "Provenance",
    "QualityFlag",
    "ReviewStatus",
    "Score",
    "SkillCode",
    # Phase 2 content variants
    "CEContent",
    "COContent",
    "EEContent",
    "EOContent",
    "ErrorAnnotation",
    "MCQ",
    "MCQOption",
    "Speaker",
    "SpeakingRubric",
    "WritingRubric",
    # Phase 2 API surface
    "DailyBlock",
    "DiagnosticAnswer",
    "DiagnosticReport",
    "DiagnosticState",
    "ErrorEnvelope",
    "LoginRequest",
    "MeProfile",
    "MockExamReport",
    "MockExamState",
    "NCLCTrajectory",
    "PlanBlock",
    "Readiness",
    "RefreshRequest",
    "SessionAnswer",
    "SessionItem",
    "SessionStart",
    "SessionState",
    "SessionSummary",
    "SignupRequest",
    "StudyPlanView",
    "SubmissionView",
    "TokenPair",
    "UpdateMeRequest",
    "WeakPoint",
    # Phase 5 additive surface
    "AccessibilityProfile",
    "DismissalLogEntry",
    "DrillKind",
    "PronunciationDisplayLabel",
    "PronunciationProsody",
    "PronunciationSignal",
]
