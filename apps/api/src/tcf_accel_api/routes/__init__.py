"""Route handlers for the tcf-accel API.

Phase 1: `healthz` only.
Phase 2: adds `auth`, `me`, `diagnostic`, `plan`, `session`, `submission`,
`mock_exam`, `insights`, `data` per `02_ARCHITECTURE.md §2.4`.
"""

from __future__ import annotations
