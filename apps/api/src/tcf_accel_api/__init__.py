"""tcf-accel HTTP API service (FastAPI).

Phase 1 exposes only `/healthz`. Phase 2 freezes the full `/v1/...` surface
from `02_ARCHITECTURE.md §2.4`; subsequent phases implement the handlers.
"""

from __future__ import annotations

__version__ = "0.1.0"
