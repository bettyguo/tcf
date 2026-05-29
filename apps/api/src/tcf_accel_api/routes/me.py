"""`/v1/me` — user profile read/update.

Phase 3 owns the canonical profile (GET / PATCH `/v1/me`).
Phase 5 (this file) lights up `GET/PATCH /v1/me/accessibility` for the
accessibility profile (ADR-029) — local-only per ADR-017; the profile
controls drill routing in `/v1/session/start`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from tcf_accel.ids import UserId
from tcf_accel.schemas.api.me import AccessibilityProfile, MeProfile, UpdateMeRequest

from tcf_accel_api.routes._stub import raise_not_implemented_for
from tcf_accel_api.state import current_user_id, get_user_state

router = APIRouter(prefix="/v1/me", tags=["me"])

_OWNER_PHASE = 3


@router.get(
    "",
    response_model=MeProfile,
    summary="Fetch the authenticated user's profile",
    responses={501: {"description": "Phase 3 owns this implementation."}},
)
async def get_me() -> MeProfile:
    """Return the authenticated user's profile."""
    raise_not_implemented_for(phase=_OWNER_PHASE, route="/v1/me")


@router.patch(
    "",
    response_model=MeProfile,
    summary="Partially update the authenticated user's profile",
    responses={501: {"description": "Phase 3 owns this implementation."}},
)
async def patch_me(_body: UpdateMeRequest) -> MeProfile:
    """Apply a partial update to the profile."""
    raise_not_implemented_for(phase=_OWNER_PHASE, route="/v1/me")


@router.get(
    "/accessibility",
    response_model=AccessibilityProfile,
    summary="Fetch the learner's accessibility profile (ADR-029)",
)
async def get_accessibility(
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> AccessibilityProfile:
    """Return the learner's accessibility preferences.

    Local-only per ADR-017; the profile drives session-time drill
    routing (e.g., `co_alternative="lexical_alt"` swaps CO drills for
    the lexical alternative — `phase5_design.md §7`).
    """
    return get_user_state(user_id).accessibility


@router.patch(
    "/accessibility",
    response_model=AccessibilityProfile,
    summary="Update the learner's accessibility profile",
)
async def patch_accessibility(
    body: AccessibilityProfile,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> AccessibilityProfile:
    """Replace the learner's accessibility profile with the submitted one."""
    state = get_user_state(user_id)
    state.accessibility = body
    return state.accessibility
