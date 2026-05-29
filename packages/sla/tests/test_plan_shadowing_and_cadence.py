"""Planner integration tests (Phase 5 step 10).

ADR-030: every default daily plan reserves a `co_shadowing` block at
≥ DEFAULT_SHADOWING_MINUTES (10 min). The reservation is carved out of
the budget *before* the bottleneck allocator runs, so production-skill
over-weighting (ADR-027) is preserved.

ADR-028 cadence post-pass: `_enforce_exam_shape_cadence` guarantees
every rolling 7-day window in the generated plan carries at least
`EXAM_SHAPE_FLOOR_MIN` minutes of exam-shape drills.
"""

from __future__ import annotations

from datetime import date

import pytest
from tcf_accel.ids import UserId
from tcf_accel.schemas.api.plan import DailyBlock, DrillType, PlanBlock
from tcf_accel_sla.estimator import bootstrap_posterior
from tcf_accel_sla.planner import PlannerInputs, generate_plan
from tcf_accel_sla.planner.allocator import SKILL_ORDER
from tcf_accel_sla.planner.generate_plan import (
    DEFAULT_SHADOWING_MINUTES,
    SHADOWING_DRILL_TYPE,
    SHADOWING_MIN_FLOOR,
    _enforce_exam_shape_cadence,
    _is_block_exam_shape,
    _reserve_shadowing,
    _shadowing_block,
)
from tcf_accel_sla.session import EXAM_SHAPE_FLOOR_MIN

_UUID_ZERO = "00000000-0000-0000-0000-000000000000"


def _user_id() -> UserId:
    from uuid import UUID  # noqa: PLC0415

    return UserId(UUID(_UUID_ZERO))


def _default_inputs(**overrides: object) -> PlannerInputs:
    base: dict[str, object] = {
        "user_id": _user_id(),
        "posteriors": {s: bootstrap_posterior(skill=s, self_report_nclc=5.0) for s in SKILL_ORDER},
        "target_nclc": 7,
        "daily_minutes_budget": 60,
        "start_date": date(2026, 6, 1),
        "horizon_days": 14,
    }
    base.update(overrides)
    return PlannerInputs(**base)  # type: ignore[arg-type]


# ─── ADR-030 — shadowing reservation ───────────────────────────


def test_reserve_shadowing_returns_default_split() -> None:
    allocator_budget, shadowing = _reserve_shadowing(60)
    assert shadowing == DEFAULT_SHADOWING_MINUTES == 10
    assert allocator_budget == 50


def test_reserve_shadowing_clamps_to_floor() -> None:
    # Asking for less than the floor must be silently raised to it.
    _, shadowing = _reserve_shadowing(60, shadowing_minutes=1)
    assert shadowing == SHADOWING_MIN_FLOOR


def test_reserve_shadowing_rejects_too_tight_budget() -> None:
    # Budget = 10 (shadowing) + 4*10 (allocator floors) = 50 minimum.
    with pytest.raises(ValueError, match="too tight"):
        _reserve_shadowing(40)


def test_shadowing_block_shape_is_canonical() -> None:
    block = _shadowing_block(10)
    assert block.skill == "CO"
    assert block.drill_type == SHADOWING_DRILL_TYPE == "shadowing"
    assert block.minutes == 10
    assert "ADR-030" in block.rationale


def test_default_plan_has_shadowing_block_every_day() -> None:
    """ADR-030: every day must carry ≥ DEFAULT_SHADOWING_MINUTES of
    shadowing on a CO block. Some days may have a *second* shadowing
    block when the planner's per-day drill rotation happens to land on
    shadowing for CO — that's additive, not a problem."""
    plan = generate_plan(_default_inputs())
    for day in plan.daily_blocks:
        shadowing_blocks = [b for b in day.blocks if b.drill_type == SHADOWING_DRILL_TYPE]
        assert len(shadowing_blocks) >= 1
        assert all(b.skill == "CO" for b in shadowing_blocks)
        total_shadowing = sum(b.minutes for b in shadowing_blocks)
        assert total_shadowing >= DEFAULT_SHADOWING_MINUTES
        # First block on the day is the canonical reservation (prepended).
        assert day.blocks[0].drill_type == SHADOWING_DRILL_TYPE
        assert day.blocks[0].minutes == DEFAULT_SHADOWING_MINUTES


def test_default_plan_total_minutes_matches_budget() -> None:
    """Sum of all blocks (incl. shadowing) equals the daily budget."""
    inputs = _default_inputs(daily_minutes_budget=90)
    plan = generate_plan(inputs)
    for day in plan.daily_blocks:
        assert day.total_minutes == 90
        assert sum(b.minutes for b in day.blocks) == 90


def test_default_plan_keeps_all_four_skills() -> None:
    """ADR-030 must not crowd out any module; every day still covers CO/CE/EE/EO."""
    plan = generate_plan(_default_inputs())
    for day in plan.daily_blocks:
        skills_covered = {b.skill for b in day.blocks}
        assert skills_covered == {"CO", "CE", "EE", "EO"}


def test_plan_rejects_too_tight_budget() -> None:
    # 49 < 10 shadowing + 4*10 allocator floor.
    with pytest.raises(ValueError, match="too tight"):
        generate_plan(_default_inputs(daily_minutes_budget=49))


def test_synthetic_cohorts_satisfy_shadowing_floor() -> None:
    """phase5_audit.md §11: every default-plan day across many cohorts
    carries ≥ DEFAULT_SHADOWING_MINUTES of shadowing."""
    # Six synthetic cohorts spanning the bottleneck-shape space.
    cohort_means = [
        {"CO": 5.0, "CE": 5.0, "EE": 5.0, "EO": 5.0},  # balanced
        {"CO": 4.0, "CE": 6.0, "EE": 7.0, "EO": 7.0},  # CO bottleneck
        {"CO": 7.0, "CE": 7.0, "EE": 4.0, "EO": 4.0},  # production bottleneck
        {"CO": 8.0, "CE": 8.0, "EE": 8.0, "EO": 8.0},  # near target
        {"CO": 3.0, "CE": 3.0, "EE": 3.0, "EO": 3.0},  # all weak
        {"CO": 9.0, "CE": 6.0, "EE": 4.0, "EO": 4.0},  # mixed
    ]
    for means in cohort_means:
        posteriors = {
            s: bootstrap_posterior(skill=s, self_report_nclc=m) for s, m in means.items()  # type: ignore[arg-type]
        }
        plan = generate_plan(_default_inputs(posteriors=posteriors))
        for day in plan.daily_blocks:
            shadowing_minutes_on_day = sum(
                b.minutes for b in day.blocks if b.drill_type == SHADOWING_DRILL_TYPE
            )
            assert shadowing_minutes_on_day >= DEFAULT_SHADOWING_MINUTES


# ─── ADR-028 — exam-shape cadence post-pass ────────────────────


def _make_day_with_drills(d: date, drill_types: list[DrillType]) -> DailyBlock:
    """Helper to construct a day with arbitrary block drill types for testing."""
    skills: list[tuple[str, int]] = [("CO", 10), ("CE", 10), ("EE", 15), ("EO", 15)]
    blocks: list[PlanBlock] = []
    for i, (skill, minutes) in enumerate(skills):
        if i < len(drill_types):
            blocks.append(
                PlanBlock(
                    skill=skill,  # type: ignore[arg-type]
                    minutes=minutes,
                    drill_type=drill_types[i],
                    rationale="test",
                ),
            )
    return DailyBlock(date=d, blocks=blocks, total_minutes=sum(b.minutes for b in blocks))


def test_cadence_pass_promotes_when_window_is_zero() -> None:
    """A plan with 7 days of pure non-exam-shape drills must be forced
    to carry at least one exam-shape block in the window."""
    days = [
        _make_day_with_drills(date(2026, 6, i + 1), ["flashcard", "cloze", "flashcard", "cloze"])
        for i in range(7)
    ]
    out = _enforce_exam_shape_cadence(days, floor_minutes=EXAM_SHAPE_FLOOR_MIN)
    # Every day's first non-shadowing, non-exam-shape block was promoted
    # on at least the days where the window was insufficient.
    promoted_any = any(
        any(_is_block_exam_shape(b) for b in d.blocks) for d in out
    )
    assert promoted_any


def test_cadence_pass_noop_when_floor_already_met() -> None:
    """Plans whose blocks are already exam-shape need no rewrite."""
    days = [
        _make_day_with_drills(
            date(2026, 6, i + 1),
            ["mock_section", "mock_section", "writing_long", "speaking_mono"],
        )
        for i in range(7)
    ]
    out = _enforce_exam_shape_cadence(days)
    # Same blocks survive (no rationale rewrites).
    for orig, new in zip(days, out, strict=True):
        for ob, nb in zip(orig.blocks, new.blocks, strict=True):
            assert ob.drill_type == nb.drill_type
            assert "exam-shape cadence" not in nb.rationale


def test_cadence_pass_preserves_shadowing_block() -> None:
    """The shadowing block (drill_type='shadowing') must never be promoted."""
    days = [
        DailyBlock(
            date=date(2026, 6, 1),
            blocks=[
                _shadowing_block(10),
                PlanBlock(skill="CO", minutes=10, drill_type="flashcard", rationale="t"),
                PlanBlock(skill="CE", minutes=10, drill_type="cloze", rationale="t"),
                PlanBlock(skill="EE", minutes=15, drill_type="flashcard", rationale="t"),
                PlanBlock(skill="EO", minutes=15, drill_type="cloze", rationale="t"),
            ],
            total_minutes=60,
        ),
    ]
    out = _enforce_exam_shape_cadence(days)
    # First block of the rewritten day is still the shadowing block.
    assert out[0].blocks[0].drill_type == SHADOWING_DRILL_TYPE
    # The next block was promoted (since the window is otherwise zero).
    promoted_block = out[0].blocks[1]
    assert _is_block_exam_shape(promoted_block)
    assert "exam-shape cadence" in promoted_block.rationale


def test_cadence_pass_total_minutes_preserved() -> None:
    """Promotion changes drill_type, not minutes — totals must stay equal."""
    days = [
        _make_day_with_drills(date(2026, 6, i + 1), ["flashcard", "cloze", "flashcard", "cloze"])
        for i in range(7)
    ]
    out = _enforce_exam_shape_cadence(days)
    for orig, new in zip(days, out, strict=True):
        assert orig.total_minutes == new.total_minutes


def test_default_plan_already_satisfies_cadence_floor() -> None:
    """Default `select_drill_type` produces writing_*/speaking_* for EE/EO
    every day — which ARE exam-shape DrillTypes — so the default plan
    trivially satisfies the cadence floor without the pass kicking in.

    This is the "happy path": the structural floor exists, but the
    default behavior doesn't need it to fire.
    """
    plan = generate_plan(_default_inputs(horizon_days=14))
    for i in range(len(plan.daily_blocks)):
        running = sum(
            b.minutes
            for d in plan.daily_blocks[max(0, i - 6) : i + 1]
            for b in d.blocks
            if _is_block_exam_shape(b)
        )
        # Production-skill blocks (writing_long + speaking_mono) total
        # 30+ min per day → 210+ min/week → far above the 30 floor.
        assert running >= EXAM_SHAPE_FLOOR_MIN
    # And no block's rationale carries the cadence-promotion marker.
    for day in plan.daily_blocks:
        for block in day.blocks:
            assert "exam-shape cadence" not in block.rationale


def test_cadence_pass_handles_empty_plan() -> None:
    assert _enforce_exam_shape_cadence([]) == []


# ─── Determinism ───────────────────────────────────────────────


def test_default_plan_is_deterministic_except_for_id_and_timestamp() -> None:
    """ADR-030 changes must preserve the plan's bytes-identical reproducibility."""
    a = generate_plan(_default_inputs())
    b = generate_plan(_default_inputs())
    # IDs and generated_at differ; everything else is identical.
    assert a.horizon_days == b.horizon_days
    assert a.rationale == b.rationale
    for da, db in zip(a.daily_blocks, b.daily_blocks, strict=True):
        assert da.date == db.date
        assert da.total_minutes == db.total_minutes
        for ba, bb in zip(da.blocks, db.blocks, strict=True):
            assert ba.skill == bb.skill
            assert ba.drill_type == bb.drill_type
            assert ba.minutes == bb.minutes
            assert ba.rationale == bb.rationale
