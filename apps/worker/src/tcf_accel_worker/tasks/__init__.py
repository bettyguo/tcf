"""Celery task modules.

Phase 1: `smoke` only.
Phase 3+: `ingest`, `synthesize`, `embed`, `quality_gate`.
Phase 4: `fsrs_optimize`, `irt_refit`.
Phase 5: `transcribe`, `align`.
Phase 6: `score_mock`.
Phase 7: `score_ee`, `score_eo`.
"""

from __future__ import annotations
