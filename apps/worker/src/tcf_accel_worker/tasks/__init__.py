"""Celery task modules.

Phase 1: `smoke` only.
Phase 3+: `ingest`, `synthesize`, `embed`, `quality_gate`.
Phase 4: `fsrs_optimize`, `irt_refit`.
Phase 5: `transcribe`, `align`.
Phase 6: `score_mock`.
Phase 7: `score_ee`, `score_eo` — scorers register on import below.
"""

from __future__ import annotations


def _install_phase7_scorers() -> None:
    """Replace the Phase 5 stub EE/EO scorers with the Phase 7 calibrated ones.

    Side-effect at import time of `tcf_accel_worker.tasks`. The
    `tcf_accel_ml.scoring` package is best-effort: when it is absent
    (e.g., a minimal worker image without the ML deps), the Phase 5
    stubs remain in the registry, and `score_ee` / `score_eo` continue
    to return the `phase7_status="stub"` payload.
    """
    try:
        from tcf_accel_ml.scoring import install_default_scorers
    except ImportError:
        return
    install_default_scorers()


_install_phase7_scorers()
