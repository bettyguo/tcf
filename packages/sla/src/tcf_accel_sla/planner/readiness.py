"""Readiness traffic-light — the single most consequential output.

`04_LEARNER_MODEL.md §2.7` + master prompt §6.2:

- 🟢 likely_ready  : P(min_skill ≥ target_NCLC) ≥ 0.80 AND all confident
- 🟡 borderline    : 0.50 ≤ P < 0.80
- 🔴 not_yet       : P < 0.50
- ⚪ insufficient  : any skill not confident

The wire-shape `Readiness` enum only carries `red | yellow | green`
(the ⚪ "insufficient data" maps to *red* on the wire so the UI never
shows green, with the textual reason explaining the gating). The
boolean test for "may we show numeric estimates at all?" is exposed
separately as `all_skills_confident`.

We never return 🟢 with any `confident=False` — that path is
explicitly tested in `tests/property/test_readiness_invariants.py`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final, Literal

from tcf_accel.schemas.api.insights import Readiness as ReadinessView
from tcf_accel.schemas.api.insights import ReadinessLight
from tcf_accel.schemas.scoring import NCLCEstimate, SkillCode

from tcf_accel_sla.estimator.nclc import SkillPosterior, to_nclc_estimate
from tcf_accel_sla.planner.allocator import SKILL_ORDER

READINESS_GREEN_THRESHOLD: Final[float] = 0.80
READINESS_YELLOW_THRESHOLD: Final[float] = 0.50

Light = Literal["red", "yellow", "green"]


def _normal_cdf(x: float) -> float:
    """Standard-normal CDF via `math.erf`; pure stdlib."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def probability_meets_target(
    posterior: SkillPosterior,
    target_nclc: int,
) -> float:
    """P(skill posterior ≥ target_nclc) under the Gaussian approximation.

    Using `posterior.mean` and `posterior.variance`:

        P(θ ≥ target) = 1 - Φ((target - μ) / σ)
    """
    sigma = posterior.stddev
    if sigma <= 0:
        return 1.0 if posterior.mean >= target_nclc else 0.0
    z = (target_nclc - posterior.mean) / sigma
    return 1.0 - _normal_cdf(z)


def compute_readiness(
    posteriors: Mapping[SkillCode, SkillPosterior],
    target_nclc: int,
    *,
    last_canonical_mock_at: object | None = None,
    canonical_mock_streak_green: int = 0,
) -> ReadinessView:
    """Compute the headline traffic-light, the reason, and the per-skill view.

    Args:
        posteriors: Per-skill posteriors; must include all 4 skills.
        target_nclc: The learner's target.
        last_canonical_mock_at: Phase 6's last canonical-mock timestamp.
        canonical_mock_streak_green: Consecutive canonical mocks at
            green. R-004 + Phase 9 launch gate require ≥ 2 for a green
            light, even if all four posteriors clear the prob threshold.

    Returns:
        `Readiness` with `light ∈ {red, yellow, green}`, populated
        per-skill estimates, and a one-paragraph reason.
    """
    per_skill: list[NCLCEstimate] = [
        to_nclc_estimate(posteriors[s]) for s in SKILL_ORDER
    ]
    all_confident = all(post.confident for post in (posteriors[s] for s in SKILL_ORDER))

    if not all_confident:
        light: ReadinessLight = "red"
        not_confident = [
            s for s in SKILL_ORDER if not posteriors[s].confident
        ]
        reason = (
            "Insufficient data — we cannot confidently estimate "
            f"{', '.join(not_confident)} yet. Complete more practice items "
            "to unlock a readiness verdict (see `04_LEARNER_MODEL.md §1.2`)."
        )
        return ReadinessView(
            light=light,
            per_skill=per_skill,
            reason=reason,
            last_canonical_mock_at=last_canonical_mock_at,  # type: ignore[arg-type]
            canonical_mock_streak_green=canonical_mock_streak_green,
        )

    # All confident: compute min-skill probability of meeting target.
    probs = [probability_meets_target(posteriors[s], target_nclc) for s in SKILL_ORDER]
    min_prob = min(probs)
    bottleneck = SKILL_ORDER[probs.index(min_prob)]

    # R-004: green requires the prob gate AND ≥ 2 consecutive canonical-mock greens.
    if min_prob >= READINESS_GREEN_THRESHOLD and canonical_mock_streak_green >= 2:
        return ReadinessView(
            light="green",
            per_skill=per_skill,
            reason=(
                f"Likely ready: P(min skill ≥ NCLC {target_nclc}) = {min_prob:.0%}; "
                f"weakest skill is {bottleneck}. "
                f"Canonical-mock green streak: {canonical_mock_streak_green}."
            ),
            last_canonical_mock_at=last_canonical_mock_at,  # type: ignore[arg-type]
            canonical_mock_streak_green=canonical_mock_streak_green,
        )

    if min_prob >= READINESS_GREEN_THRESHOLD:
        # Posteriors say green but mock streak hasn't earned it.
        return ReadinessView(
            light="yellow",
            per_skill=per_skill,
            reason=(
                f"Posteriors suggest you're ready (P = {min_prob:.0%} on {bottleneck}), "
                f"but the launch gate requires ≥ 2 consecutive canonical-mock greens. "
                f"Current streak: {canonical_mock_streak_green}."
            ),
            last_canonical_mock_at=last_canonical_mock_at,  # type: ignore[arg-type]
            canonical_mock_streak_green=canonical_mock_streak_green,
        )

    if min_prob >= READINESS_YELLOW_THRESHOLD:
        return ReadinessView(
            light="yellow",
            per_skill=per_skill,
            reason=(
                f"Borderline: P(min skill ≥ NCLC {target_nclc}) = {min_prob:.0%}; "
                f"{bottleneck} is the bottleneck. Continue the plan; revisit in 1–2 weeks."
            ),
            last_canonical_mock_at=last_canonical_mock_at,  # type: ignore[arg-type]
            canonical_mock_streak_green=canonical_mock_streak_green,
        )

    return ReadinessView(
        light="red",
        per_skill=per_skill,
        reason=(
            f"Not yet: P(min skill ≥ NCLC {target_nclc}) = {min_prob:.0%}; "
            f"{bottleneck} is far below target. Do not book the exam yet."
        ),
        last_canonical_mock_at=last_canonical_mock_at,  # type: ignore[arg-type]
        canonical_mock_streak_green=canonical_mock_streak_green,
    )


__all__ = [
    "READINESS_GREEN_THRESHOLD",
    "READINESS_YELLOW_THRESHOLD",
    "Light",
    "compute_readiness",
    "probability_meets_target",
]
