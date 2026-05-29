"""`/v1/plan/*` — study plan read/regenerate. Phase 4 implementation.

Wires the planner from `packages/sla/src/tcf_accel_sla/planner/` to the
frozen Phase 2 API surface. Persistence is the in-process store from
`tcf_accel_api.state` (Phase 5 swap to Postgres).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from tcf_accel.ids import UserId
from tcf_accel.schemas.api.plan import DailyBlock, StudyPlanView
from tcf_accel_sla.planner import PlannerInputs, generate_plan

from tcf_accel_api.state import current_user_id, get_user_state

router = APIRouter(prefix="/v1/plan", tags=["plan"])

_OWNER_PHASE = 4


@router.get(
    "",
    response_model=StudyPlanView,
    summary="Fetch the current rolling study plan",
)
async def get_plan(
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> StudyPlanView:
    """Return the active plan; 404 with `E_NOT_FOUND` if none exists yet."""
    st = get_user_state(user_id)
    if st.plan is None:
        # Auto-generate on first access — Phase 4 spec §2.6 says the
        # plan is the planner's headline output; failing to find one
        # because the user hasn't called regenerate yet would be a
        # papercut. The diagnostic flow normally writes the plan, but
        # we don't gate read on that.
        st.plan = generate_plan(
            PlannerInputs(
                user_id=user_id,
                posteriors=st.posteriors,
                target_nclc=st.target_nclc,
                daily_minutes_budget=st.daily_minutes_budget,
                start_date=datetime.now(UTC).date(),
            ),
        )
    return st.plan


@router.post(
    "/regenerate",
    response_model=StudyPlanView,
    summary="Force a plan regeneration",
)
async def regenerate(
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> StudyPlanView:
    """Generate a new plan and supersede the previous one."""
    st = get_user_state(user_id)
    st.plan = generate_plan(
        PlannerInputs(
            user_id=user_id,
            posteriors=st.posteriors,
            target_nclc=st.target_nclc,
            daily_minutes_budget=st.daily_minutes_budget,
            start_date=datetime.now(UTC).date(),
        ),
    )
    return st.plan


@router.get(
    "/today",
    response_model=list[DailyBlock],
    summary="Fetch today's blocks only",
)
async def today(
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> list[DailyBlock]:
    """Return only today's blocks (subset of `GET /v1/plan`)."""
    plan = await get_plan(user_id)
    today_date = datetime.now(UTC).date()
    todays = [b for b in plan.daily_blocks if b.date == today_date]
    if not todays:
        # Plan was generated on an earlier day and doesn't include
        # today; regenerate and try again.
        plan = await regenerate(user_id)
        todays = [b for b in plan.daily_blocks if b.date == today_date]
    if not todays:
        raise HTTPException(
            status_code=404,
            detail="No plan blocks for today; regenerate the plan.",
        )
    return todays
