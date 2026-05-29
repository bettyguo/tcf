"""Auto-scoring pipeline (Phase 7).

Surfaces the EE/EO scorers, the calibration layer, and the LLM critic
protocol. The Celery hand-off (`tcf_accel_worker.tasks.score_ee` /
`score_eo`) imports `install_default_scorers()` from this package at
worker boot, replacing the Phase 5 stubs registered there.

Direct import of `tcf_accel_ml.scoring` is **side-effect-free**: the
default registrations only happen when `install_default_scorers()` is
called explicitly. The worker bootstrap does that; tests build their
own scorers without touching the global registry.
"""

from __future__ import annotations

from tcf_accel_ml.scoring.calibrate.calibrator import RubricCalibrator
from tcf_accel_ml.scoring.calibrate.kappa import quadratic_weighted_kappa
from tcf_accel_ml.scoring.calibrate.ridge import Ridge
from tcf_accel_ml.scoring.ee.score import EEScorer, EEScoringResult, EEWorkerScorer
from tcf_accel_ml.scoring.eo.score import EOScorer, EOScoringResult, EOWorkerScorer
from tcf_accel_ml.scoring.feedback import FeedbackBlock, render_feedback
from tcf_accel_ml.scoring.inflation_guard import apply_inflation_guard
from tcf_accel_ml.scoring.llm.critic import LLMCritic, LLMCritique, SuggestedRewrite
from tcf_accel_ml.scoring.llm.stub import LLMCriticStub
from tcf_accel_ml.scoring.rubric_table import nclc_from_total_20


def install_default_scorers() -> None:
    """Register EE+EO scorers under their canonical rubric versions.

    Idempotent: re-registration replaces the previous scorer for the
    same `rubric_version` (Phase 5's registry contract).
    """
    from tcf_accel_worker.tasks.score_ee import register_scorer as register_ee
    from tcf_accel_worker.tasks.score_eo import register_scorer as register_eo

    register_ee("ee.v1", EEWorkerScorer())
    register_eo("eo.v1", EOWorkerScorer())


__all__ = [
    "EEScorer",
    "EEScoringResult",
    "EEWorkerScorer",
    "EOScorer",
    "EOScoringResult",
    "EOWorkerScorer",
    "FeedbackBlock",
    "LLMCritic",
    "LLMCriticStub",
    "LLMCritique",
    "Ridge",
    "RubricCalibrator",
    "SuggestedRewrite",
    "apply_inflation_guard",
    "install_default_scorers",
    "nclc_from_total_20",
    "quadratic_weighted_kappa",
    "render_feedback",
]
