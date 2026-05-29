"""`/v1/health` — versioned liveness probe.

Same shape as `/healthz` but mounted under the `/v1/` namespace so clients
that consume only `/v1/*` can probe without depending on the unversioned
liveness route.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from tcf_accel.schemas.version import SCHEMA_VERSION

router = APIRouter(prefix="/v1", tags=["meta"])


class V1HealthResponse(BaseModel):
    """Versioned health response."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok")
    phase: int = Field(default=2, description="The phase that owns the current API surface (frozen contract).")
    schema_version: str = Field(default=SCHEMA_VERSION)
    api_version: str = Field(default="v1")


@router.get("/health", response_model=V1HealthResponse, summary="Versioned liveness probe")
async def v1_health() -> V1HealthResponse:
    """Liveness probe under `/v1/`."""
    return V1HealthResponse()
