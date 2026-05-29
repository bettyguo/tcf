"""Bottleneck-weighted daily time allocator.

Master prompt §2.3 + `04_LEARNER_MODEL.md §2.5` + ADR-027:

Given today's minute budget, the per-skill posterior, and the target
NCLC, return how many minutes to spend on each skill so that the
*weakest* skill — and in particular the production skills (EE, EO) —
gets disproportionate time.

The formula:

    α_s = max(ε, (target - μ_s))² · β_s
    minutes_s = total_minutes · α_s / Σ α

with a floor of `SKILL_FLOOR_MINUTES` per skill to avoid neglect, and a
post-floor re-normalization so the sum equals `total_minutes`.

`β_s` over-weights the production skills (EE 1.4, EO 1.5) per the
audit's "production-skill floor" requirement.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from tcf_accel.schemas.scoring import SkillCode

from tcf_accel_sla.estimator.nclc import NCLC_MAX, SkillPosterior

# Canonical skill iteration order — keeps allocator output deterministic
# across Python versions (dict insertion order is fine on 3.12 but we
# defend against accidental re-ordering).
SKILL_ORDER: Final[tuple[SkillCode, ...]] = ("CO", "CE", "EE", "EO")

PRODUCTION_SKILL_BETA: Final[Mapping[SkillCode, float]] = {"EE": 1.4, "EO": 1.5}
RECEPTION_SKILL_BETA: Final[Mapping[SkillCode, float]] = {"CO": 1.0, "CE": 0.9}
SKILL_BETAS: Final[Mapping[SkillCode, float]] = {
    **RECEPTION_SKILL_BETA,
    **PRODUCTION_SKILL_BETA,
}

SKILL_FLOOR_MINUTES: Final[int] = 10
EPSILON: Final[float] = 0.01  # avoid 0² when learner is already at target


def allocate(
    total_minutes: int,
    posteriors: Mapping[SkillCode, SkillPosterior],
    target_nclc: int,
) -> dict[SkillCode, int]:
    """Return integer minute allocations summing to `total_minutes`.

    Args:
        total_minutes: Today's budget; must be ≥ 4 × floor (so every
            skill can take at least its floor).
        posteriors: Per-skill posteriors. Missing skills raise `KeyError`.
        target_nclc: The learner's NCLC target (typically 7..11).

    Returns:
        `{skill: minutes}` for all four skills, summing to `total_minutes`.
        Order matches `SKILL_ORDER`.

    Raises:
        ValueError: If `total_minutes < 4 * SKILL_FLOOR_MINUTES`, or if
            `target_nclc` is out of range.
        KeyError: If `posteriors` is missing any of CO/CE/EE/EO.
    """
    if total_minutes < len(SKILL_ORDER) * SKILL_FLOOR_MINUTES:
        msg = (
            f"total_minutes={total_minutes} below 4×floor "
            f"({len(SKILL_ORDER) * SKILL_FLOOR_MINUTES}); cannot allocate."
        )
        raise ValueError(msg)
    if not (1 <= target_nclc <= int(NCLC_MAX)):
        msg = f"target_nclc out of range: {target_nclc}"
        raise ValueError(msg)

    # Raw alphas — bigger when skill is further below target, scaled by β.
    alphas: dict[SkillCode, float] = {}
    for skill in SKILL_ORDER:
        post = posteriors[skill]  # KeyError surfaces missing-skill bug
        gap = max(0.0, float(target_nclc) - post.mean)
        alphas[skill] = max(EPSILON, gap * gap) * SKILL_BETAS[skill]

    total_alpha = sum(alphas.values())
    raw = {
        skill: total_minutes * a / total_alpha
        for skill, a in alphas.items()
    }
    return _enforce_floor_and_round(raw, floor=SKILL_FLOOR_MINUTES, total=total_minutes)


def _enforce_floor_and_round(
    raw: Mapping[SkillCode, float],
    *,
    floor: int,
    total: int,
) -> dict[SkillCode, int]:
    """Enforce per-skill floor; round to integers; absorb rounding into largest skill.

    Algorithm:
    1. Apply floor: any skill below `floor` is raised to `floor`.
    2. Renormalize the *unfloored* skills' shares to absorb the diff.
    3. Round each skill to int; adjust the largest skill by the rounding
       residual so the integer total matches `total`.
    """
    floored: dict[SkillCode, float] = {}
    fixed_minutes = 0.0
    unfloored: list[SkillCode] = []
    for skill in SKILL_ORDER:
        if raw[skill] < floor:
            floored[skill] = float(floor)
            fixed_minutes += floor
        else:
            unfloored.append(skill)

    remaining = float(total) - fixed_minutes
    raw_unfloored_sum = sum(raw[s] for s in unfloored)
    if unfloored and raw_unfloored_sum > 0:
        for skill in unfloored:
            floored[skill] = remaining * raw[skill] / raw_unfloored_sum
    elif unfloored:
        # All raw values were 0 (degenerate); split evenly.
        share = remaining / len(unfloored)
        for skill in unfloored:
            floored[skill] = share

    # Round, then push the residual into the largest skill so the
    # integer sum equals `total` exactly.
    rounded = {skill: round(floored[skill]) for skill in SKILL_ORDER}
    diff = total - sum(rounded.values())
    if diff != 0:
        # Pick the skill with the largest *floored* allocation; bias toward
        # production skills on ties (deterministic order).
        ordered = sorted(
            SKILL_ORDER,
            key=lambda s: (-floored[s], -SKILL_BETAS[s], s),
        )
        rounded[ordered[0]] += diff

    return rounded


__all__ = [
    "EPSILON",
    "PRODUCTION_SKILL_BETA",
    "RECEPTION_SKILL_BETA",
    "SKILL_BETAS",
    "SKILL_FLOOR_MINUTES",
    "SKILL_ORDER",
    "allocate",
]
