"""Bottleneck-driven planner: time allocator, study-plan generator, readiness light.

See `04_LEARNER_MODEL.md §2.5–2.7` and ADR-027 for the contract.
"""

from __future__ import annotations

from tcf_accel_sla.planner.allocator import (
    PRODUCTION_SKILL_BETA,
    RECEPTION_SKILL_BETA,
    SKILL_BETAS,
    SKILL_FLOOR_MINUTES,
    SKILL_ORDER,
    allocate,
)
from tcf_accel_sla.planner.generate_plan import (
    PlannerInputs,
    generate_plan,
    select_drill_type,
    simulate_learning,
)
from tcf_accel_sla.planner.readiness import (
    READINESS_GREEN_THRESHOLD,
    READINESS_YELLOW_THRESHOLD,
    Light,
    compute_readiness,
    probability_meets_target,
)

__all__ = [
    "PRODUCTION_SKILL_BETA",
    "READINESS_GREEN_THRESHOLD",
    "READINESS_YELLOW_THRESHOLD",
    "RECEPTION_SKILL_BETA",
    "SKILL_BETAS",
    "SKILL_FLOOR_MINUTES",
    "SKILL_ORDER",
    "Light",
    "PlannerInputs",
    "allocate",
    "compute_readiness",
    "generate_plan",
    "probability_meets_target",
    "select_drill_type",
    "simulate_learning",
]
