"""Scheduler, estimator, planner, and readiness logic for tcf-accel.

Phase 4 surface (`04_LEARNER_MODEL.md`):

- `tcf_accel_sla.scheduler.fsrs` — FSRS-6 wrapper (pure stdlib).
- `tcf_accel_sla.scheduler.lector` — semantic-confusable spacing.
- `tcf_accel_sla.estimator.nclc` — Bayesian per-skill posterior.
- `tcf_accel_sla.diagnostic.cat` — computer-adaptive testing.
- `tcf_accel_sla.planner.allocator` — bottleneck-weighted time allocation.
- `tcf_accel_sla.planner.generate_plan` — 12-week rolling plan generator.
- `tcf_accel_sla.planner.readiness` — traffic-light booking advice.

The top-level re-exports below are the common entry points; for the
full surface, import the submodules directly.
"""

from __future__ import annotations

from tcf_accel_sla.diagnostic import CandidateItem, DiagnosticSession
from tcf_accel_sla.estimator import (
    SkillPosterior,
    bootstrap_posterior,
    to_nclc_estimate,
    update_with_mcq,
    update_with_rubric,
)
from tcf_accel_sla.planner import (
    PlannerInputs,
    allocate,
    compute_readiness,
    generate_plan,
    probability_meets_target,
)
from tcf_accel_sla.scheduler import (
    Card,
    FSRSScheduler,
    Rating,
    adjust_due_with_lector,
)

__version__ = "0.1.0"

__all__ = [
    "CandidateItem",
    "Card",
    "DiagnosticSession",
    "FSRSScheduler",
    "PlannerInputs",
    "Rating",
    "SkillPosterior",
    "adjust_due_with_lector",
    "allocate",
    "bootstrap_posterior",
    "compute_readiness",
    "generate_plan",
    "probability_meets_target",
    "to_nclc_estimate",
    "update_with_mcq",
    "update_with_rubric",
]
