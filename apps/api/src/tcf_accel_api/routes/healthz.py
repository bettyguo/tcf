"""Liveness probe.

Used by docker-compose healthchecks and CI smoke tests. Does not touch the
database or any side-effecting backend — this is "is the process up?", not
"is the system healthy?". Phase 9 adds a `/readyz` for the deep check.

Example:
    >>> from fastapi.testclient import TestClient
    >>> from tcf_accel_api.main import app
    >>> TestClient(app).get("/healthz").status_code
    200

Complexity: O(1).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from tcf_accel.schemas.version import SCHEMA_VERSION

router = APIRouter(tags=["meta"])


class HealthResponse(BaseModel):
    """Healthz response payload."""

    status: Literal["ok"] = "ok"
    phase: int = Field(description="Current build-phase number; sanity-checked in tests.")
    schema_version: str = Field(description="`tcf_accel.schemas.version.SCHEMA_VERSION`.")


@router.get("/healthz", response_model=HealthResponse, summary="Liveness probe")
async def healthz() -> HealthResponse:
    """Return a fixed payload indicating the process is alive.

    Returns:
        A `HealthResponse` with `status="ok"` and the current schema version.
    """
    return HealthResponse(status="ok", phase=2, schema_version=SCHEMA_VERSION)
