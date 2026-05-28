"""tcf-accel Celery worker.

Phase 1 ships only a smoke task. Later phases register tasks for content
ingestion, scoring, scheduling-job orchestration, and IRT refit.
"""

from __future__ import annotations

__version__ = "0.1.0"
