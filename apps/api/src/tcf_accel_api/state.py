"""In-process state for Phase 4 routes.

The Phase 4 spec does not require persistence — the planner outputs are
deterministic given inputs, and the diagnostic session is naturally
in-memory between client requests. Phase 5+ replaces these dicts with
Redis (sessions) and Postgres (plans) without touching the route shape.

The stores are deliberately *per-process*: the API in v1 runs single-
worker, and these are wiped on restart. Tests reset state via
`reset_all()` or by overriding the `current_user_id` dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Final
from uuid import UUID

from tcf_accel.ids import UserId
from tcf_accel.schemas.api.me import AccessibilityProfile
from tcf_accel.schemas.api.plan import StudyPlanView
from tcf_accel.schemas.scoring import SkillCode
from tcf_accel_sla.diagnostic import DiagnosticSession
from tcf_accel_sla.estimator import SkillPosterior, bootstrap_posterior


@dataclass
class DiagnosticUmbrella:
    """All four per-skill CAT sessions for one diagnostic run."""

    started_at: datetime
    sessions: dict[SkillCode, DiagnosticSession] = field(default_factory=dict)


@dataclass
class UserState:
    """All Phase-4-relevant state for one user, in one process."""

    posteriors: dict[SkillCode, SkillPosterior]
    plan: StudyPlanView | None = None
    target_nclc: int = 7
    daily_minutes_budget: int = 60
    diagnostics: dict[UUID, DiagnosticUmbrella] = field(default_factory=dict)
    canonical_mock_streak_green: int = 0
    accessibility: AccessibilityProfile = field(default_factory=AccessibilityProfile)


_STORE: Final[dict[UserId, UserState]] = {}
_LOCK: Final[Lock] = Lock()


def _default_posteriors() -> dict[SkillCode, SkillPosterior]:
    """Fresh per-skill priors centered on B1 (NCLC 5)."""
    return {
        skill: bootstrap_posterior(skill=skill, self_report_nclc=5.0)
        for skill in ("CO", "CE", "EE", "EO")
    }


def get_user_state(user_id: UserId) -> UserState:
    """Return (or lazily create) the state for one user."""
    with _LOCK:
        st = _STORE.get(user_id)
        if st is None:
            st = UserState(posteriors=_default_posteriors())
            _STORE[user_id] = st
        return st


def start_diagnostic(user_id: UserId, session_id: UUID) -> DiagnosticUmbrella:
    """Create + register a fresh diagnostic umbrella for the user."""
    st = get_user_state(user_id)
    umbrella = DiagnosticUmbrella(started_at=datetime.now(UTC))
    st.diagnostics[session_id] = umbrella
    return umbrella


def get_diagnostic(user_id: UserId, session_id: UUID) -> DiagnosticUmbrella | None:
    """Return the user's named diagnostic umbrella, or None."""
    st = get_user_state(user_id)
    return st.diagnostics.get(session_id)


def reset_user_state(user_id: UserId) -> None:
    """Drop the user's in-process state. Used by tests."""
    with _LOCK:
        _STORE.pop(user_id, None)


def reset_all() -> None:
    """Drop all in-process state. Used by tests."""
    with _LOCK:
        _STORE.clear()


# The "current user" id is a stub until Phase 3 wires real auth.
# Tests can override this via FastAPI's dependency-override hook.
DEFAULT_USER_ID: Final[UserId] = UserId(
    UUID("11111111-1111-4111-8111-111111111111"),
)


def current_user_id() -> UserId:
    """FastAPI dependency: returns the request's user id.

    Phase 3 replaces this with a JWT/claims extractor; Phase 4 uses a
    fixed UUID so the planner endpoints work without auth wired up yet.
    """
    return DEFAULT_USER_ID


__all__ = [
    "DEFAULT_USER_ID",
    "DiagnosticUmbrella",
    "UserState",
    "current_user_id",
    "get_diagnostic",
    "get_user_state",
    "reset_all",
    "reset_user_state",
    "start_diagnostic",
]
