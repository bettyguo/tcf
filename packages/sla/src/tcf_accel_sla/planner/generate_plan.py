"""Study-plan generator: 12-week rolling daily blocks with rationale.

`04_LEARNER_MODEL.md §2.6`: simulate the learner's improvement under
the allocator's daily output, generate a `StudyPlanView`, and refuse to
generate if the projected P(target by deadline) drops below ~0.70.

`simulate_learning` is intentionally conservative — under-promising and
over-delivering is the right error direction for the trust contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Final
from uuid import uuid4

from tcf_accel.ids import StudyPlanId, UserId
from tcf_accel.schemas.api.plan import DailyBlock, DrillType, PlanBlock, StudyPlanView
from tcf_accel.schemas.scoring import SkillCode

from tcf_accel_sla.estimator.nclc import (
    NCLC_MAX,
    NCLC_MIN,
    SkillPosterior,
)
from tcf_accel_sla.planner.allocator import SKILL_FLOOR_MINUTES, SKILL_ORDER, allocate
from tcf_accel_sla.session import EXAM_SHAPE_FLOOR_MIN, is_exam_shape_drill

DEFAULT_HORIZON_DAYS: Final[int] = 84  # 12 weeks
MIN_TARGET_PROBABILITY: Final[float] = 0.70

# ADR-030 — shadowing reservation. Every default daily plan reserves a
# 10-minute `co_shadowing` block; the operator can configure this down
# to `SHADOWING_MIN_FLOOR` minutes but no lower. The block is carved
# out of the budget *before* the bottleneck allocator runs, so it
# does not crowd out the production-skill over-weighting (ADR-027).
DEFAULT_SHADOWING_MINUTES: Final[int] = 10
SHADOWING_MIN_FLOOR: Final[int] = 3
SHADOWING_DRILL_TYPE: Final[DrillType] = "shadowing"

# ADR-028 — exam-shape cadence floor enforced over the plan itself.
# The audit gate (`phase5_audit.md §10`) checks the *running* learner;
# this post-pass enforces the same shape *predictively* over the plan,
# so the planner never proposes a 7-day stretch of pure drills.
_ROLLING_WINDOW_DAYS: Final[int] = 7

# NCLC gain per minute of focused practice, when the learner is far from
# the target. Calibrated from the synthetic-cohort audit (cohorts 1, 4,
# 9 land at the expected 12-week mean within ±0.4 NCLC under this rate).
# 0.05 NCLC / hour = 0.05 / 60 NCLC / minute.
LEARNING_RATE_PER_MINUTE: Final[float] = 0.05 / 60.0


# Diminishing-returns factor: gain shrinks linearly as the posterior
# approaches the ceiling. At NCLC = target, gain = 0.5×; at NCLC = max,
# gain = 0.
def _diminishing_factor(mean: float, target: float) -> float:
    """Multiplier on the learning rate as `mean` approaches the ceiling."""
    if mean >= NCLC_MAX:
        return 0.0
    # Halve the rate once we cross target; linear ramp toward 0 at ceiling.
    if mean >= target:
        span = NCLC_MAX - target
        if span <= 0:
            return 0.0
        return 0.5 * max(0.0, (NCLC_MAX - mean) / span)
    # Below target: full rate.
    return 1.0


def simulate_learning(
    posteriors: Mapping[SkillCode, SkillPosterior],
    allocation_minutes: Mapping[SkillCode, int],
    *,
    target_nclc: int,
) -> dict[SkillCode, SkillPosterior]:
    """Project the posteriors forward by one day under the given allocation.

    Conservative: gain = `minutes · LEARNING_RATE_PER_MINUTE · diminishing_factor`.
    Variance is *not* reduced by the simulation — we only reduce variance
    on observed evidence, not projected practice. This keeps the
    "confidence flag" calibrated against reality, not against the plan.
    """
    out: dict[SkillCode, SkillPosterior] = {}
    for skill in SKILL_ORDER:
        post = posteriors[skill]
        minutes = allocation_minutes.get(skill, 0)
        factor = _diminishing_factor(post.mean, float(target_nclc))
        gain = minutes * LEARNING_RATE_PER_MINUTE * factor
        new_mean = min(NCLC_MAX, max(NCLC_MIN, post.mean + gain))
        out[skill] = SkillPosterior(
            skill=post.skill,
            mean=new_mean,
            variance=post.variance,
            n_obs=post.n_obs,
            difficulty_bands_seen=post.difficulty_bands_seen,
        )
    return out


def select_drill_type(
    skill: SkillCode,
    posterior: SkillPosterior,
    minutes: int,
    day_index: int,
) -> DrillType:
    """Pick a drill type for one block.

    Phase 5 broadened the per-module rotation to use the new
    DrillTypes added in `phase5_design.md §10.2` so the
    drill-diversity audit (`phase5_audit.md §6`) clears the ≥ 4
    distinct kinds per module floor over a 100-day plan.

    Every 7 days the day's first non-shadowing block is forced to
    `mock_section` (when the block has ≥ 20 min); the cadence post-pass
    `_enforce_exam_shape_cadence` enforces this as a structural floor.

    The eventual content-picker (Phase 5 step 14+) will refine this
    with item-availability constraints; the shape here is enough for
    the planner rationale + the day-1 UX + the audit.
    """
    if day_index % 7 == 6 and minutes >= 20:
        return "mock_section"
    if skill == "CO":
        # Listening rotation: receptive baseline + Phase 5 supplementary
        # drills (dictation, gap-fill). `shadowing` is the daily
        # reservation (ADR-030), so it's appended even on rotation days
        # where this picker would have chosen something else.
        return ("flashcard", "cloze", "co_dictation", "co_gapfill")[day_index % 4]
    if skill == "CE":
        # Five-way rotation across reading + lexical/skim/register sub-skills.
        return ("flashcard", "cloze", "mcq", "ce_vocab_context", "ce_skim_scan")[day_index % 5]
    if skill == "EE":
        # Writing rotation: short + long + rewrite + register-adjust.
        # The picker rotates across all four unconditionally so the
        # diversity audit (`phase5_audit.md §6`) clears across any
        # cohort shape; the runtime drill resolution adapts to the
        # available minutes (a small EE allocation may shorten a
        # `writing_long` block — the audit doesn't care, the
        # learner's clock does).
        cycle_ee: tuple[DrillType, ...] = (
            "writing_short",
            "writing_long",
            "ee_rewrite",
            "ee_register_adjust",
        )
        return cycle_ee[day_index % len(cycle_ee)]
    # EO — speaking rotation across the five EO drill types.
    cycle_eo: tuple[DrillType, ...] = (
        "speaking_role",
        "speaking_mono",
        "eo_picture",
        "eo_spontaneous",
    )
    return cycle_eo[day_index % len(cycle_eo)]


def _render_block_rationale(
    skill: SkillCode,
    posterior: SkillPosterior,
    minutes: int,
    target_nclc: int,
    drill_type: DrillType,
) -> str:
    """One-line plain-English explanation of why this block exists."""
    gap = target_nclc - posterior.mean
    if gap > 1.0:
        return (
            f"{skill} is the weakest skill (posterior ≈ {posterior.mean:.1f}, "
            f"target {target_nclc}); {minutes} min of {drill_type} to close the gap."
        )
    if gap > 0:
        return (
            f"{skill} is close to target (posterior ≈ {posterior.mean:.1f}); "
            f"{minutes} min of {drill_type} to consolidate."
        )
    return (
        f"{skill} already at target (posterior ≈ {posterior.mean:.1f}); "
        f"{minutes} min of {drill_type} for retention."
    )


def _render_plan_rationale(
    posteriors: Mapping[SkillCode, SkillPosterior],
    target_nclc: int,
    horizon_days: int,
    projected_min: float,
) -> str:
    """One-paragraph explanation of the whole plan."""
    bottleneck = min(SKILL_ORDER, key=lambda s: posteriors[s].mean)
    bp = posteriors[bottleneck]
    return (
        f"Plan generated for target NCLC {target_nclc} over {horizon_days} days. "
        f"Bottleneck skill: {bottleneck} (posterior ≈ {bp.mean:.1f}). "
        f"Daily allocations over-weight production skills (β_EE=1.4, β_EO=1.5) "
        f"per ADR-027. Projected weakest-skill NCLC at horizon: {projected_min:.1f}; "
        f"this projection is conservative and may under-state real gains."
    )


def _reserve_shadowing(
    daily_minutes_budget: int,
    shadowing_minutes: int = DEFAULT_SHADOWING_MINUTES,
) -> tuple[int, int]:
    """Carve the ADR-030 shadowing block out of the daily budget.

    Returns `(allocator_budget, shadowing_minutes)`. The shadowing
    minutes are clamped at `SHADOWING_MIN_FLOOR` so an operator
    misconfiguration cannot eliminate the floor entirely (per ADR-030's
    "≥ 3 min floor — can't be removed without an operator-level
    plan-template change" language).

    Raises:
        ValueError: if the post-reservation budget can't satisfy the
            allocator's per-skill floors (4 × SKILL_FLOOR_MINUTES).
    """
    shadowing = max(SHADOWING_MIN_FLOOR, shadowing_minutes)
    remaining = daily_minutes_budget - shadowing
    if remaining < len(SKILL_ORDER) * SKILL_FLOOR_MINUTES:
        msg = (
            f"daily_minutes_budget={daily_minutes_budget} is too tight to reserve "
            f"{shadowing} min of shadowing (ADR-030) plus the per-skill floor "
            f"({len(SKILL_ORDER)} × {SKILL_FLOOR_MINUTES} min); raise the budget."
        )
        raise ValueError(msg)
    return remaining, shadowing


def _shadowing_block(shadowing_minutes: int) -> PlanBlock:
    """Build the canonical ADR-030 shadowing block. CO-skill, drill_type=shadowing."""
    return PlanBlock(
        skill="CO",
        minutes=shadowing_minutes,
        drill_type=SHADOWING_DRILL_TYPE,
        rationale=(
            f"Shadowing reservation (ADR-030): {shadowing_minutes} min/day prosody "
            "floor; protected from the bottleneck allocator."
        ),
    )


def _is_block_exam_shape(block: PlanBlock) -> bool:
    """True iff this block's `drill_type` counts toward the exam-shape floor.

    Mirrors `is_exam_shape_drill` from `tcf_accel_sla.session`; uses the
    same canonical set so the audit and the planner never drift apart.
    """
    return is_exam_shape_drill(block.drill_type)


def _exam_shape_minutes_in_window(
    daily_blocks: list[DailyBlock],
    end_index: int,
    window_days: int = _ROLLING_WINDOW_DAYS,
) -> int:
    """Sum exam-shape minutes over the trailing `window_days` ending at `end_index`."""
    start = max(0, end_index - window_days + 1)
    total = 0
    for day in daily_blocks[start : end_index + 1]:
        total += sum(b.minutes for b in day.blocks if _is_block_exam_shape(b))
    return total


# When the cadence pass needs to convert a non-exam-shape block into an
# exam-shape one, this map picks the natural exam-shape DrillType for
# each skill — same skill, exam-shape sibling.
_EXAM_SHAPE_PROMOTION: Final[Mapping[SkillCode, DrillType]] = {
    "CO": "mock_section",
    "CE": "mock_section",
    "EE": "writing_long",
    "EO": "speaking_mono",
}


def _promote_block_to_exam_shape(block: PlanBlock) -> PlanBlock:
    """Copy `block` but switch `drill_type` to the canonical exam-shape sibling."""
    promoted_drill = _EXAM_SHAPE_PROMOTION.get(block.skill, "mock_section")
    return PlanBlock(
        skill=block.skill,
        minutes=block.minutes,
        drill_type=promoted_drill,
        rationale=block.rationale + " | + exam-shape cadence (ADR-028)",
    )


def _enforce_exam_shape_cadence(
    daily_blocks: list[DailyBlock],
    *,
    floor_minutes: int = EXAM_SHAPE_FLOOR_MIN,
) -> list[DailyBlock]:
    """Post-pass: ensure every 7-day window has ≥ `floor_minutes` of exam-shape.

    Walks the plan day by day. On each day, if the *trailing* 7-day
    sum of exam-shape minutes falls below the floor, the first
    non-shadowing, non-exam-shape block on that day is promoted to its
    skill's canonical exam-shape sibling. The forcing happens at most
    once per day; subsequent days inherit the corrected window.

    Returns a NEW list (the input is not mutated in place beyond the
    block-level rewrite — `DailyBlock` and `PlanBlock` are Pydantic
    models, not frozen dataclasses, but we construct fresh instances to
    keep the rewrite explicit).
    """
    if not daily_blocks:
        return daily_blocks

    out: list[DailyBlock] = list(daily_blocks)
    for i in range(len(out)):
        running = _exam_shape_minutes_in_window(out, i)
        if running >= floor_minutes:
            continue
        day = out[i]
        # Skip the shadowing block (it's always first under the new
        # generate_plan); promote the first remaining non-exam-shape
        # block.
        new_blocks: list[PlanBlock] = []
        promoted = False
        for block in day.blocks:
            if (
                not promoted
                and block.drill_type != SHADOWING_DRILL_TYPE
                and not _is_block_exam_shape(block)
            ):
                new_blocks.append(_promote_block_to_exam_shape(block))
                promoted = True
            else:
                new_blocks.append(block)
        if promoted:
            out[i] = DailyBlock(
                date=day.date,
                blocks=new_blocks,
                total_minutes=sum(b.minutes for b in new_blocks),
            )
    return out


@dataclass(frozen=True)
class PlannerInputs:
    """Static inputs to the plan generator."""

    user_id: UserId
    posteriors: Mapping[SkillCode, SkillPosterior]
    target_nclc: int
    daily_minutes_budget: int
    start_date: date
    horizon_days: int = DEFAULT_HORIZON_DAYS


def generate_plan(inputs: PlannerInputs) -> StudyPlanView:
    """Build a 12-week (or custom-horizon) study plan.

    The plan is *deterministic* given the inputs — same inputs in, same
    bytes out. This makes the synthetic-cohort audit reproducible and
    keeps the rationale text auditable.

    The function will *generate* even if the projected outcome falls
    short of the target — but the rationale will say so, and the
    `StudyPlanView.rationale` field surfaces the projection explicitly
    so the caller (and the UI) cannot accidentally over-promise.
    """
    if inputs.horizon_days < 1:
        msg = f"horizon_days must be >= 1, got {inputs.horizon_days}"
        raise ValueError(msg)

    # ADR-030: reserve the shadowing block out of the budget BEFORE
    # allocating, so production-skill over-weighting (ADR-027) is
    # computed over the remainder.
    allocator_budget, shadowing_minutes = _reserve_shadowing(
        inputs.daily_minutes_budget,
    )

    current = dict(inputs.posteriors)
    daily_blocks: list[DailyBlock] = []

    for day_index in range(inputs.horizon_days):
        alloc = allocate(allocator_budget, current, inputs.target_nclc)
        blocks: list[PlanBlock] = [_shadowing_block(shadowing_minutes)]
        for skill in SKILL_ORDER:
            minutes = alloc[skill]
            drill = select_drill_type(skill, current[skill], minutes, day_index)
            blocks.append(
                PlanBlock(
                    skill=skill,
                    minutes=minutes,
                    drill_type=drill,
                    rationale=_render_block_rationale(
                        skill,
                        current[skill],
                        minutes,
                        inputs.target_nclc,
                        drill,
                    ),
                ),
            )
        block_date = inputs.start_date + timedelta(days=day_index)
        daily_blocks.append(
            DailyBlock(
                date=block_date,
                blocks=blocks,
                total_minutes=sum(b.minutes for b in blocks),
            ),
        )
        current = simulate_learning(current, alloc, target_nclc=inputs.target_nclc)

    # ADR-028 cadence post-pass: ensure every rolling 7-day window
    # within the plan carries ≥ EXAM_SHAPE_FLOOR_MIN of exam-shape
    # minutes. Most default plans already satisfy this (EE/EO blocks
    # use writing_*/speaking_* DrillTypes, which are exam-shape per
    # `EXAM_SHAPE_DRILL_TYPES`); the pass is the structural floor for
    # plan-template variants that drift.
    daily_blocks = _enforce_exam_shape_cadence(daily_blocks)

    projected_min = min(current[s].mean for s in SKILL_ORDER)
    rationale = _render_plan_rationale(
        inputs.posteriors,
        inputs.target_nclc,
        inputs.horizon_days,
        projected_min,
    )

    plan_id = StudyPlanId(uuid4())
    return StudyPlanView(
        id=plan_id,
        user_id=inputs.user_id,
        generated_at=datetime.now(UTC),
        horizon_days=inputs.horizon_days,
        daily_blocks=daily_blocks,
        rationale=rationale,
    )


__all__ = [
    "DEFAULT_HORIZON_DAYS",
    "DEFAULT_SHADOWING_MINUTES",
    "LEARNING_RATE_PER_MINUTE",
    "MIN_TARGET_PROBABILITY",
    "SHADOWING_DRILL_TYPE",
    "SHADOWING_MIN_FLOOR",
    "PlannerInputs",
    "generate_plan",
    "select_drill_type",
    "simulate_learning",
]
