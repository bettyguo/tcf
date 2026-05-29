"""`/v1/insights/*` — derived views over the learner's history.

Phase 4 implements **readiness** only (the launch-blocking headline per
`04_LEARNER_MODEL.md §2.7`). `nclc-trajectory` and `weak-points` stay
Phase 8 stubs — they need Phase 5 interaction history and Phase 8
weak-point clustering that don't exist yet.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from tcf_accel.ids import UserId
from tcf_accel.schemas.api.insights import NCLCTrajectory, Readiness, WeakPoint
from tcf_accel_sla.planner import compute_readiness

from tcf_accel_api.routes._stub import raise_not_implemented_for
from tcf_accel_api.state import current_user_id, get_user_state

router = APIRouter(prefix="/v1/insights", tags=["insights"])

_PHASE_8 = 8


@router.get(
    "/nclc-trajectory",
    response_model=NCLCTrajectory,
    summary="Historical per-skill NCLC + forecast",
    responses={501: {"description": "Phase 8 owns this implementation."}},
)
async def trajectory() -> NCLCTrajectory:
    """Return the trajectory series."""
    raise_not_implemented_for(phase=_PHASE_8, route="/v1/insights/nclc-trajectory")


@router.get(
    "/weak-points",
    response_model=list[WeakPoint],
    summary="Top error patterns per skill",
    responses={501: {"description": "Phase 8 owns this implementation."}},
)
async def weak_points() -> list[WeakPoint]:
    """Return the ranked weak-point list."""
    raise_not_implemented_for(phase=_PHASE_8, route="/v1/insights/weak-points")


@router.get(
    "/readiness",
    response_model=Readiness,
    summary="Traffic-light 'ready to book the exam?' answer",
)
async def readiness(
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> Readiness:
    """Compute the readiness traffic light from the current posteriors.

    Phase 4 (this route) is the gate that enforces "no green without
    confidence" — the planner is forbidden by ADR-025 from showing
    green when any skill's `confident=False`.
    """
    st = get_user_state(user_id)
    return compute_readiness(
        posteriors=st.posteriors,
        target_nclc=st.target_nclc,
        canonical_mock_streak_green=st.canonical_mock_streak_green,
    )
