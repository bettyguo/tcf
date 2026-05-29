"""`/v1/data/*` — learner-owned data export + erasure. Phase 9 implements.

These two routes are the ownership half of the privacy contract:

- `GET /v1/data/export` streams the user's full history as NDJSON.
- `DELETE /v1/data` triggers GDPR-style soft-delete (`users.deleted_at`)
  with a scheduled purge.

Phase 2 freezes the wire shape so the Phase 8 UI can wire the buttons
before Phase 9 ships the durable implementation.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from tcf_accel_api.routes._stub import raise_not_implemented_for

router = APIRouter(prefix="/v1/data", tags=["data"])

_OWNER_PHASE = 9


class DataDeleteResponse(BaseModel):
    """Returned by `DELETE /v1/data` after a successful soft-delete."""

    model_config = ConfigDict(extra="forbid")

    deleted: bool
    scheduled_purge_at: datetime


@router.get(
    "/export",
    summary="Stream the authenticated user's full history as NDJSON",
    responses={
        200: {
            "content": {"application/x-ndjson": {}},
            "description": "NDJSON stream of every interaction, submission, plan, and estimate.",
        },
        501: {"description": "Phase 9 owns this implementation."},
    },
)
async def export() -> None:
    """Stream the user's data as NDJSON."""
    raise_not_implemented_for(phase=_OWNER_PHASE, route="/v1/data/export")


@router.delete(
    "",
    response_model=DataDeleteResponse,
    summary="Schedule erasure of the authenticated user's account",
    responses={501: {"description": "Phase 9 owns this implementation."}},
)
async def delete_data() -> DataDeleteResponse:
    """Soft-delete the user; durable purge runs nightly."""
    raise_not_implemented_for(phase=_OWNER_PHASE, route="/v1/data")
