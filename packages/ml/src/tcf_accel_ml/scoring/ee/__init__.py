"""EE rubric scorer (Phase 7).

`install_default_scorer()` is exposed here so the worker can register
the calibrated EE scorer without an explicit import dance.
"""

from __future__ import annotations

from tcf_accel_ml.scoring.ee.score import EEScorer, EEScoringResult, EEWorkerScorer

__all__ = ["EEScorer", "EEScoringResult", "EEWorkerScorer"]
