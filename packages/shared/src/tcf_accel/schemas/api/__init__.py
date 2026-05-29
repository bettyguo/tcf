"""Request/response models for the frozen `/v1/` API surface.

Phase 2 freezes the wire shape of every `/v1/` route. Each module under
this subpackage owns the schemas for one route group; see
`02_ARCHITECTURE.md §2.4` and `phase2_design.md §4.4` for the canonical
route table.

Phase 3+ implementations consume these schemas; they may *add* optional
fields (additive only — ADR-016) without breaking the wire.
"""

from __future__ import annotations

from tcf_accel.schemas.api.auth import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
)
from tcf_accel.schemas.api.diagnostic import (
    DiagnosticAnswer,
    DiagnosticReport,
    DiagnosticState,
)
from tcf_accel.schemas.api.errors import ErrorEnvelope
from tcf_accel.schemas.api.insights import NCLCTrajectory, Readiness, WeakPoint
from tcf_accel.schemas.api.me import AccessibilityProfile, MeProfile, UpdateMeRequest
from tcf_accel.schemas.api.mock_exam import MockExamReport, MockExamState
from tcf_accel.schemas.api.plan import DailyBlock, DrillKind, PlanBlock, StudyPlanView
from tcf_accel.schemas.api.session import (
    DismissalLogEntry,
    SessionAnswer,
    SessionItem,
    SessionStart,
    SessionState,
    SessionSummary,
)
from tcf_accel.schemas.api.submission import SubmissionView

__all__ = [
    "AccessibilityProfile",
    "DailyBlock",
    "DiagnosticAnswer",
    "DiagnosticReport",
    "DiagnosticState",
    "DismissalLogEntry",
    "DrillKind",
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
]
