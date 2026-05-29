"""Bayesian per-skill NCLC estimator.

See `04_LEARNER_MODEL.md §2.3` and ADR-025 for the contract; this
package implements it.
"""

from __future__ import annotations

from tcf_accel_sla.estimator.nclc import (
    CONFIDENT_MAX_VARIANCE,
    CONFIDENT_MIN_OBS,
    CONFIDENT_MIN_SPREAD,
    NCLC_MAX,
    NCLC_MIN,
    SkillPosterior,
    bootstrap_posterior,
    fisher_information,
    irt_p_correct,
    to_nclc_estimate,
    update_with_mcq,
    update_with_rubric,
)

__all__ = [
    "CONFIDENT_MAX_VARIANCE",
    "CONFIDENT_MIN_OBS",
    "CONFIDENT_MIN_SPREAD",
    "NCLC_MAX",
    "NCLC_MIN",
    "SkillPosterior",
    "bootstrap_posterior",
    "fisher_information",
    "irt_p_correct",
    "to_nclc_estimate",
    "update_with_mcq",
    "update_with_rubric",
]
