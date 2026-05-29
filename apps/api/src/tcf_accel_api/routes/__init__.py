"""Route handlers for the tcf-accel API.

Phase 1: `healthz` only.
Phase 2 (this file): adds `/v1/` route groups per `02_ARCHITECTURE.md §2.4`:
`health`, `auth`, `me`, `diagnostic`, `plan`, `session`, `submission`,
`mock_exam`, `insights`, `data`. Every Phase 2 handler returns 501 via
`NotImplementedRouteError` with the phase that owns the implementation.
Phases 3–8 replace the stubs with real handlers.

Phase 4 implementations are live: `health`, `me` accessibility,
`diagnostic`, `plan`, `insights/readiness`.
Phase 5 implementations are live: `session/*`.
Phase 6 implementations are live: `mock-exam/*` (this phase).
"""

from __future__ import annotations
