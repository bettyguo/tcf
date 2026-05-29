"""Helper for Phase 2 501-stub routes.

Every Phase 2 `/v1/` route raises `NotImplementedRouteError` via
`raise_not_implemented_for(phase=N)`. The resulting `HTTPException` body
matches `ErrorEnvelope` (`phase2_design.md §4.3`), so the wire shape
matches what Phase 3+ implementations will eventually return on real
errors.
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException
from tcf_accel.errors import NotImplementedRouteError


def raise_not_implemented_for(*, phase: int, route: str) -> NoReturn:
    """Raise the canonical 501 for a Phase 2 stub route.

    Args:
        phase: The build-phase number that owns the eventual handler
            (e.g., 3 for auth, 4 for plan, 5 for session, 6 for mock-exam,
            7 for submission, 8 for insights, 9 for data).
        route: Path of the calling route; included in the error context
            for client debugging.

    Raises:
        HTTPException: status 501 with `ErrorEnvelope`-shaped detail.
    """
    err = NotImplementedRouteError(phase=phase, route=route)
    raise HTTPException(status_code=err.http_status, detail=err.to_envelope(phase=phase))


__all__ = ["raise_not_implemented_for"]
