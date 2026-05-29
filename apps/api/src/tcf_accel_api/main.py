"""FastAPI application entry point.

Phase 1 exposed only `/healthz`. Phase 2 freezes the full `/v1/...`
surface (`02_ARCHITECTURE.md §2.4`, `phase2_design.md §4`); every
Phase 2 route is registered with its Pydantic request/response models
and returns 501 via `NotImplementedRouteError` until the owning phase
fills in the handler.

Example:
    >>> from fastapi.testclient import TestClient
    >>> from tcf_accel_api.main import app
    >>> client = TestClient(app)
    >>> client.get("/healthz").json()["status"]
    'ok'
    >>> r = client.get("/v1/health")
    >>> r.status_code
    200
    >>> r = client.get("/v1/session/start")  # still a Phase 5 stub
    >>> r.status_code in (404, 405, 501)  # method check vs handler differs
    True

Complexity: O(1) per request; total routers registered: 11 (Phase 2 freeze).
"""

from __future__ import annotations

from typing import Final

from fastapi import FastAPI
from tcf_accel.schemas.version import SCHEMA_VERSION

from tcf_accel_api import __version__
from tcf_accel_api.routes import (
    auth,
    data,
    diagnostic,
    health,
    healthz,
    insights,
    me,
    mock_exam,
    plan,
    session,
    submission,
)

API_TITLE: Final[str] = "tcf-accel API"
PHASE: Final[int] = 6


def create_app() -> FastAPI:
    """Construct the FastAPI application.

    Factored so tests can build isolated instances with their own
    dependency overrides. Phase 2 registers every Phase-3-through-9
    route as a 501-stub; the eventual implementations replace the
    stubs without changing the registered shape.

    Example:
        >>> app = create_app()
        >>> app.title
        'tcf-accel API'

    Complexity: O(N) in the number of registered routers (Phase 2: 11
    including the unversioned `/healthz`).
    """
    app = FastAPI(
        title=API_TITLE,
        version=__version__,
        description=(
            "tcf-accel HTTP API. Phase 2 freezes the /v1/ contract from "
            "`02_ARCHITECTURE.md §2.4`; Phases 3–8 implement the handlers."
        ),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
    )
    # Unversioned liveness (Phase 1).
    app.include_router(healthz.router)
    # Versioned routers (Phase 2 freeze).
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(diagnostic.router)
    app.include_router(plan.router)
    app.include_router(session.router)
    app.include_router(submission.router)
    app.include_router(mock_exam.router)
    app.include_router(insights.router)
    app.include_router(data.router)
    return app


app: Final[FastAPI] = create_app()


__all__ = ["PHASE", "SCHEMA_VERSION", "app", "create_app"]
