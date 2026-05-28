"""FastAPI application entry point.

Example:
    >>> from fastapi.testclient import TestClient
    >>> from tcf_accel_api.main import app
    >>> client = TestClient(app)
    >>> client.get("/healthz").json()
    {'status': 'ok', 'phase': 1, 'schema_version': '0.1.0'}

Complexity: O(1) per request for Phase 1's single endpoint.
"""

from __future__ import annotations

from typing import Final

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from tcf_accel.schemas.version import SCHEMA_VERSION

from tcf_accel_api import __version__
from tcf_accel_api.routes import healthz

API_TITLE: Final[str] = "tcf-accel API"
PHASE: Final[int] = 1


def create_app() -> FastAPI:
    """Construct the FastAPI application.

    Factored so tests can build isolated instances with their own dependency overrides.

    Example:
        >>> app = create_app()
        >>> app.title
        'tcf-accel API'

    Complexity: O(N) in the number of registered routers (Phase 1: 1).
    """
    app = FastAPI(
        title=API_TITLE,
        version=__version__,
        description=(
            "tcf-accel HTTP API. Phase 1 ships /healthz only; the full "
            "/v1/... surface is frozen in Phase 2 (`02_ARCHITECTURE.md`)."
        ),
        default_response_class=ORJSONResponse,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
    )
    app.include_router(healthz.router)
    return app


app: Final[FastAPI] = create_app()


__all__ = ["PHASE", "SCHEMA_VERSION", "app", "create_app"]
