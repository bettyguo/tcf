"""`/v1/auth/*` — sign-up, login, refresh. Phase 3 implements; Phase 2 stubs."""

from __future__ import annotations

from fastapi import APIRouter
from tcf_accel.schemas.api.auth import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
)

from tcf_accel_api.routes._stub import raise_not_implemented_for

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_OWNER_PHASE = 3


@router.post(
    "/signup",
    response_model=TokenPair,
    status_code=201,
    summary="Create a new account",
    responses={501: {"description": "Phase 3 owns this implementation."}},
)
async def signup(_body: SignupRequest) -> TokenPair:
    """Create an account and return a token pair."""
    raise_not_implemented_for(phase=_OWNER_PHASE, route="/v1/auth/signup")


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Exchange credentials for a token pair",
    responses={501: {"description": "Phase 3 owns this implementation."}},
)
async def login(_body: LoginRequest) -> TokenPair:
    """Authenticate and return a token pair."""
    raise_not_implemented_for(phase=_OWNER_PHASE, route="/v1/auth/login")


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Refresh the access token",
    responses={501: {"description": "Phase 3 owns this implementation."}},
)
async def refresh(_body: RefreshRequest) -> TokenPair:
    """Exchange a refresh token for a new access token."""
    raise_not_implemented_for(phase=_OWNER_PHASE, route="/v1/auth/refresh")
