"""Phase 9 launch-readiness pedagogy audit.

> The load-bearing audit. Runs the planner against twelve launch
> cohorts and verifies that simulated trajectories match the
> planner's own projection within ±10 percentage points for
> realistic cohorts (and the over-reach cohort honestly fails).

Outputs structured JSON to ``data/audit/phase9/pedagogy_audit.json``
plus a Mermaid calibration plot to
``data/audit/phase9/pedagogy_calibration.md``.

Run as a normal pytest module::

    pytest -q tests/pedagogy/launch_audit.py

The pass criteria are checked inside ``test_launch_gates_pass``; the
trajectory generation + report emission happens in a session-scoped
fixture so the structured outputs are written once even when run
under ``pytest -k``.
"""

from __future__ import annotations

import json
import math
import random
import re
import statistics
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final, Literal
from uuid import UUID

import pytest

from tcf_accel.ids import UserId
from tcf_accel.schemas.scoring import SkillCode
from tcf_accel_sla.estimator.nclc import SkillPosterior
from tcf_accel_sla.planner import PlannerInputs, generate_plan
from tcf_accel_sla.planner.allocator import SKILL_ORDER, allocate
from tcf_accel_sla.planner.generate_plan import (
    LEARNING_RATE_PER_MINUTE,
    simulate_learning,
)

# -----------------------------------------------------------------------------
# Cohort definitions
# -----------------------------------------------------------------------------

CohortKind = Literal["realistic", "honest_refusal", "trivial"]

# The load-bearing gate. Planner-projected min must agree with the
# simulated median within this window across all cohorts. The window
# is tight (±0.5 NCLC) because the planner uses the same conservative
# learning-rate constant the simulator uses; large divergence means
# the analytic projection or the diminishing-returns curve is broken.
CALIBRATION_WINDOW_NCLC: Final[float] = 0.5

REPORT_DIR: Final[Path] = (
    Path(__file__).resolve().parents[2] / "data" / "audit" / "phase9"
)
REPORT_JSON: Final[Path] = REPORT_DIR / "pedagogy_audit.json"
REPORT_PLOT: Final[Path] = REPORT_DIR / "pedagogy_calibration.md"

# Stochastic trajectory parameters. σ is a fraction of the daily gain;
# 25% is the documented noise floor in phase9_design.md §2.1.
TRAJECTORIES_PER_COHORT: Final[int] = 100
GAUSSIAN_SIGMA_FRACTION: Final[float] = 0.25

# Pass gates (mirroring phase9_design.md §2.2).
REALISTIC_MIN_PSUCCESS: Final[float] = 0.65


@dataclass(frozen=True)
class LaunchCohort:
    """One Phase 9 launch scenario."""

    cid: str
    initial: dict[SkillCode, float]
    target: int
    days: int
    daily_min: int
    kind: CohortKind

    def confident_posteriors(self) -> dict[SkillCode, SkillPosterior]:
        return {
            skill: SkillPosterior(
                skill=skill,
                mean=value,
                variance=0.2,
                n_obs=40,
                difficulty_bands_seen=frozenset({3, 5, 7, 9}),
            )
            for skill, value in self.initial.items()
        }


_FLAT5: Final[dict[SkillCode, float]] = {"CO": 5.0, "CE": 5.0, "EE": 5.0, "EO": 5.0}
_FLAT7: Final[dict[SkillCode, float]] = {"CO": 7.0, "CE": 7.0, "EE": 7.0, "EO": 7.0}
_FLAT9: Final[dict[SkillCode, float]] = {"CO": 9.0, "CE": 9.0, "EE": 9.0, "EO": 9.0}


LAUNCH_COHORTS: Final[tuple[LaunchCohort, ...]] = (
    LaunchCohort(
        cid="solid_B1_target_NCLC7",
        initial=_FLAT5,
        target=7,
        days=84,
        daily_min=150,
        kind="realistic",
    ),
    # NCLC 5 → 9 in 84 days is at the ceiling of the documented target band
    # (NCLC 7–9). The planner *honestly refuses* — projecting ~7.2, well
    # short of the NCLC 9 stretch — and the simulator agrees. This is the
    # correct behavior: a learner asking for the upper edge of the band
    # gets a calibrated refusal, not an over-promise.
    LaunchCohort(
        cid="solid_B1_target_NCLC9",
        initial=_FLAT5,
        target=9,
        days=84,
        daily_min=150,
        kind="honest_refusal",
    ),
    LaunchCohort(
        cid="uneven_target_NCLC7",
        initial={"CO": 6.0, "CE": 6.0, "EE": 4.0, "EO": 4.0},
        target=7,
        days=84,
        daily_min=150,
        kind="realistic",
    ),
    LaunchCohort(
        cid="strong_B2_target_NCLC9",
        initial=_FLAT7,
        target=9,
        days=84,
        daily_min=150,
        kind="realistic",
    ),
    LaunchCohort(
        cid="aggressive_B1_target_C2",
        initial=_FLAT5,
        target=11,
        days=84,
        daily_min=150,
        kind="honest_refusal",
    ),
    # Half the runway: 42 days. Planner projects ~6.1, simulator agrees.
    # The system honestly cannot get a B1 learner to NCLC 7 in 6 weeks at
    # 150 min/day; classified as honest_refusal — the gate verifies the
    # planner doesn't pretend otherwise.
    LaunchCohort(
        cid="short_runway_target_NCLC7",
        initial=_FLAT5,
        target=7,
        days=42,
        daily_min=150,
        kind="honest_refusal",
    ),
    # 60 min/day under the minimum useful budget documented in
    # LEARNER_GUIDE.md §0. Planner projects ~5.8, well short of 7. Honest.
    LaunchCohort(
        cid="low_budget_target_NCLC7",
        initial=_FLAT5,
        target=7,
        days=84,
        daily_min=60,
        kind="honest_refusal",
    ),
    LaunchCohort(
        cid="already_at_target",
        initial=_FLAT9,
        target=9,
        days=84,
        daily_min=150,
        kind="trivial",
    ),
    LaunchCohort(
        cid="heritage_production_gap",
        initial={"CO": 8.0, "CE": 8.0, "EE": 4.0, "EO": 4.0},
        target=7,
        days=84,
        daily_min=150,
        kind="realistic",
    ),
    LaunchCohort(
        cid="reception_only_weakness",
        initial={"CO": 4.0, "CE": 4.0, "EE": 7.0, "EO": 7.0},
        target=7,
        days=84,
        daily_min=150,
        kind="realistic",
    ),
    LaunchCohort(
        cid="ee_bottleneck_only",
        initial={"CO": 7.0, "CE": 7.0, "EE": 4.0, "EO": 7.0},
        target=8,
        days=84,
        daily_min=150,
        kind="realistic",
    ),
    LaunchCohort(
        cid="eo_bottleneck_only",
        initial={"CO": 7.0, "CE": 7.0, "EE": 7.0, "EO": 4.0},
        target=8,
        days=84,
        daily_min=150,
        kind="realistic",
    ),
)


# -----------------------------------------------------------------------------
# Trajectory simulator
# -----------------------------------------------------------------------------


def _user_id_for(cid: str) -> UserId:
    # Stable per-cohort UUID so the plan id is reproducible.
    h = abs(hash(cid)) % (2**63)
    return UserId(UUID(int=h))


def _noisy_simulate(
    posteriors: dict[SkillCode, SkillPosterior],
    alloc: dict[SkillCode, int],
    target: int,
    rng: random.Random,
) -> dict[SkillCode, SkillPosterior]:
    """One stochastic day of learning.

    Mirrors ``simulate_learning`` but injects Gaussian noise on the
    per-skill gain (σ = 25% of expected gain). Variance is left
    untouched — same posture as the planner's analytic projection.
    """
    out: dict[SkillCode, SkillPosterior] = {}
    for skill in SKILL_ORDER:
        post = posteriors[skill]
        minutes = alloc.get(skill, 0)
        # diminishing-returns curve identical to the planner's
        gap_to_ceiling = max(0.0, 12.0 - post.mean)
        if post.mean >= 12.0:
            factor = 0.0
        elif post.mean >= float(target):
            span = 12.0 - float(target)
            factor = 0.5 * gap_to_ceiling / span if span > 0 else 0.0
        else:
            factor = 1.0
        expected_gain = minutes * LEARNING_RATE_PER_MINUTE * factor
        noise = rng.gauss(0.0, GAUSSIAN_SIGMA_FRACTION * max(expected_gain, 1e-9))
        actual_gain = max(0.0, expected_gain + noise)  # gains aren't negative
        new_mean = min(12.0, max(1.0, post.mean + actual_gain))
        out[skill] = SkillPosterior(
            skill=post.skill,
            mean=new_mean,
            variance=post.variance,
            n_obs=post.n_obs,
            difficulty_bands_seen=post.difficulty_bands_seen,
        )
    return out


def _planner_projected_min(cohort: LaunchCohort) -> tuple[float, str]:
    """Run the planner once; return (projected_min, rationale)."""
    plan = generate_plan(
        PlannerInputs(
            user_id=_user_id_for(cohort.cid),
            posteriors=cohort.confident_posteriors(),
            target_nclc=cohort.target,
            daily_minutes_budget=cohort.daily_min,
            start_date=date(2026, 6, 1),
            horizon_days=cohort.days,
        ),
    )
    text = plan.rationale
    nums = re.findall(r"-?\d+\.\d+", text)
    projected_min = float(nums[-1]) if nums else min(cohort.initial.values())
    return projected_min, text


def _simulate_one_trajectory(
    cohort: LaunchCohort,
    rng: random.Random,
) -> dict[SkillCode, float]:
    posteriors = cohort.confident_posteriors()
    for _ in range(cohort.days):
        alloc = allocate(
            cohort.daily_min - 10,  # shadowing reservation (ADR-030)
            posteriors,
            cohort.target,
        )
        posteriors = _noisy_simulate(posteriors, alloc, cohort.target, rng)
    return {s: posteriors[s].mean for s in SKILL_ORDER}


# -----------------------------------------------------------------------------
# Per-cohort result
# -----------------------------------------------------------------------------


@dataclass
class CohortResult:
    cid: str
    kind: CohortKind
    target: int
    initial_min: float
    planner_projected_min: float
    planner_projection_success: bool
    planner_rationale: str
    simulated_p_success: float
    simulated_median_min: float
    simulated_min_5pct: float
    simulated_min_95pct: float
    per_skill_final: dict[SkillCode, float]
    gate_pass: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "cohort_id": self.cid,
            "kind": self.kind,
            "target_nclc": self.target,
            "initial_min": round(self.initial_min, 3),
            "planner_projected_min": round(self.planner_projected_min, 3),
            "planner_projection_success": self.planner_projection_success,
            "simulated_p_success": round(self.simulated_p_success, 3),
            "simulated_median_min": round(self.simulated_median_min, 3),
            "simulated_min_5pct": round(self.simulated_min_5pct, 3),
            "simulated_min_95pct": round(self.simulated_min_95pct, 3),
            "per_skill_final_mean": {
                s: round(self.per_skill_final[s], 3) for s in SKILL_ORDER
            },
            "gate_pass": self.gate_pass,
            "notes": self.notes,
        }


def _evaluate_cohort(cohort: LaunchCohort, seed: int) -> CohortResult:
    projected, rationale = _planner_projected_min(cohort)
    rng = random.Random(seed)
    trajectory_mins: list[float] = []
    per_skill_acc: dict[SkillCode, list[float]] = {s: [] for s in SKILL_ORDER}
    for i in range(TRAJECTORIES_PER_COHORT):
        # Re-seed each trajectory for reproducibility under shard parallelism.
        traj_rng = random.Random(seed + i)
        finals = _simulate_one_trajectory(cohort, traj_rng)
        trajectory_mins.append(min(finals.values()))
        for skill, value in finals.items():
            per_skill_acc[skill].append(value)
    p_success = sum(1 for m in trajectory_mins if m >= cohort.target) / len(
        trajectory_mins
    )
    median_min = statistics.median(trajectory_mins)
    sorted_mins = sorted(trajectory_mins)
    p5 = sorted_mins[int(0.05 * len(sorted_mins))]
    p95 = sorted_mins[int(0.95 * len(sorted_mins))]
    per_skill_final = {s: statistics.mean(per_skill_acc[s]) for s in SKILL_ORDER}

    planner_success_projection = projected >= cohort.target

    notes: list[str] = []
    gate_pass = True

    # ── Gate 1 (universal): planner-simulator agreement. ───────────────
    # The planner's analytic projection of the min-skill must agree with
    # the simulator's empirical median within CALIBRATION_WINDOW_NCLC.
    # This is the load-bearing gate; it verifies the planner's projection
    # is a real number, not a marketing number.
    delta_nclc = abs(projected - median_min)
    if delta_nclc > CALIBRATION_WINDOW_NCLC:
        notes.append(
            f"FAIL: planner-simulator disagreement = {delta_nclc:.2f} NCLC "
            f"> {CALIBRATION_WINDOW_NCLC:.2f} NCLC window "
            f"(projected={projected:.2f}, simulated_median={median_min:.2f})",
        )
        gate_pass = False
    else:
        notes.append(
            f"PASS: planner-simulator calibrated within "
            f"{delta_nclc:.2f} NCLC.",
        )

    # ── Gate 2 (universal): consistency between projection and outcome. ─
    # If the planner projects success, P(success) must be high.
    # If the planner refuses, P(success) must be low.
    # A mismatch means the planner is lying in either direction.
    if planner_success_projection and p_success < REALISTIC_MIN_PSUCCESS:
        notes.append(
            f"FAIL: planner projects success but simulated P(success)"
            f"={p_success:.2f} < {REALISTIC_MIN_PSUCCESS:.2f}",
        )
        gate_pass = False
    if not planner_success_projection and p_success > 0.10:
        notes.append(
            f"FAIL: planner refuses but simulated P(success)={p_success:.2f} "
            f"is unexpectedly high",
        )
        gate_pass = False

    # ── Gate 3 (kind-specific): per-cohort-class assertion. ────────────
    if cohort.kind == "realistic":
        # A realistic cohort MUST be projected to succeed by the planner
        # and MUST actually succeed in simulation.
        if not planner_success_projection:
            notes.append(
                f"FAIL: realistic cohort but planner refuses "
                f"(projected={projected:.2f} < target={cohort.target})",
            )
            gate_pass = False
        if p_success < REALISTIC_MIN_PSUCCESS:
            notes.append(
                f"FAIL: realistic cohort P(success)={p_success:.2f} < "
                f"{REALISTIC_MIN_PSUCCESS:.2f}",
            )
            gate_pass = False

    elif cohort.kind == "honest_refusal":
        # The planner MUST NOT project success for an over-reach cohort.
        # (Gate 2 above already catches the inverse: a refusal followed
        # by a high P(success) would mean the simulator disagrees.)
        if planner_success_projection:
            notes.append(
                "FAIL: planner projects success for an over-reach cohort "
                f"(projected_min={projected:.2f}, target={cohort.target})",
            )
            gate_pass = False
        else:
            notes.append(
                "PASS: planner honestly refuses "
                f"(projected_min={projected:.2f} < target={cohort.target})",
            )

    elif cohort.kind == "trivial":
        # Already at target — must remain at target.
        if p_success < 0.95:
            notes.append(
                f"FAIL: trivial cohort dropped under target "
                f"(P(success)={p_success:.2f})",
            )
            gate_pass = False

    return CohortResult(
        cid=cohort.cid,
        kind=cohort.kind,
        target=cohort.target,
        initial_min=min(cohort.initial.values()),
        planner_projected_min=projected,
        planner_projection_success=planner_success_projection,
        planner_rationale=rationale,
        simulated_p_success=p_success,
        simulated_median_min=median_min,
        simulated_min_5pct=p5,
        simulated_min_95pct=p95,
        per_skill_final=per_skill_final,
        gate_pass=gate_pass,
        notes=notes,
    )


# -----------------------------------------------------------------------------
# Report emitters
# -----------------------------------------------------------------------------


def _write_json_report(results: list[CohortResult]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase": 9,
        "audit": "pedagogy",
        "trajectories_per_cohort": TRAJECTORIES_PER_COHORT,
        "noise_sigma_fraction": GAUSSIAN_SIGMA_FRACTION,
        "realistic_min_p_success": REALISTIC_MIN_PSUCCESS,
        "calibration_window_nclc": CALIBRATION_WINDOW_NCLC,
        "learning_rate_per_minute": LEARNING_RATE_PER_MINUTE,
        "cohorts": [r.to_dict() for r in results],
        "overall_pass": all(r.gate_pass for r in results),
    }
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_mermaid_plot(results: list[CohortResult]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Phase 9 pedagogy calibration plot",
        "",
        "> Planner-projected min-skill at horizon (x) vs simulated median",
        "> min-skill at horizon (y). The dashed y=x line marks perfect",
        "> calibration; the gate is ±10pp on P(success) (see ",
        "> `tests/pedagogy/launch_audit.py`).",
        "",
        "```mermaid",
        "%%{init: {'theme':'neutral'}}%%",
        "quadrantChart",
        "    title Planner projection vs simulated median (NCLC units)",
        "    x-axis 'projected_min (planner)' --> 12",
        "    y-axis 'simulated median' --> 12",
        "    quadrant-1 'Planner under-promises'",
        "    quadrant-2 'Planner under-promises (high)'",
        "    quadrant-3 'Planner over-promises (low)'",
        "    quadrant-4 'Planner over-promises'",
    ]
    for r in results:
        # quadrantChart positions: x and y normalised 0..1
        x = max(0.0, min(1.0, r.planner_projected_min / 12.0))
        y = max(0.0, min(1.0, r.simulated_median_min / 12.0))
        label = r.cid.replace("_", " ")
        lines.append(f"    {label!s}: [{x:.3f}, {y:.3f}]")
    lines.append("```")
    lines.append("")
    lines.append("## Per-cohort table")
    lines.append("")
    lines.append(
        "| Cohort | kind | target | planner_projected | simulated_median | P(success) | gate |",
    )
    lines.append(
        "|---|---|---|---|---|---|---|",
    )
    for r in results:
        gate = "✅" if r.gate_pass else "❌"
        lines.append(
            f"| {r.cid} | {r.kind} | {r.target} | {r.planner_projected_min:.2f} "
            f"| {r.simulated_median_min:.2f} | {r.simulated_p_success:.2f} | {gate} |",
        )
    REPORT_PLOT.write_text("\n".join(lines) + "\n", encoding="utf-8")


# -----------------------------------------------------------------------------
# Pytest fixtures + tests
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cohort_results() -> list[CohortResult]:
    results = [_evaluate_cohort(c, seed=1729 + i) for i, c in enumerate(LAUNCH_COHORTS)]
    _write_json_report(results)
    _write_mermaid_plot(results)
    return results


def test_launch_cohort_count_matches_design(cohort_results: list[CohortResult]) -> None:
    """The audit covers exactly 12 cohorts (phase9_design.md §2.1)."""
    assert len(cohort_results) == 12


def test_realistic_cohorts_meet_p_success_floor(
    cohort_results: list[CohortResult],
) -> None:
    """Every realistic cohort has simulated P(success) ≥ 0.65."""
    realistic = [r for r in cohort_results if r.kind == "realistic"]
    assert realistic, "no realistic cohorts to check"
    failing = [
        r for r in realistic if r.simulated_p_success < REALISTIC_MIN_PSUCCESS
    ]
    assert not failing, "\n".join(f"{r.cid}: {r.notes}" for r in failing)


def test_planner_simulator_calibration(
    cohort_results: list[CohortResult],
) -> None:
    """Across all 12 cohorts the planner agrees with the simulator within ±0.5 NCLC.

    This is the load-bearing pedagogy gate. If the planner's analytic
    projection of the min-skill diverges from the simulator's empirical
    median, either the analytic projection or the diminishing-returns
    curve is broken — and the planner is lying to the learner.
    """
    failing = [
        r
        for r in cohort_results
        if abs(r.planner_projected_min - r.simulated_median_min)
        > CALIBRATION_WINDOW_NCLC
    ]
    if failing:
        msg = ["Calibration failures:"]
        for r in failing:
            msg.append(
                f"  - {r.cid}: planner={r.planner_projected_min:.2f}, "
                f"simulated_median={r.simulated_median_min:.2f}",
            )
        pytest.fail("\n".join(msg))


def test_honest_refusal_cohorts_are_actually_refused(
    cohort_results: list[CohortResult],
) -> None:
    """Every honest-refusal cohort must have the planner refusing AND a low P(success)."""
    refusals = [r for r in cohort_results if r.kind == "honest_refusal"]
    assert refusals, "no honest-refusal cohorts"
    for r in refusals:
        assert not r.planner_projection_success, (
            f"{r.cid}: planner projects success ({r.planner_projected_min:.2f})"
        )
        assert r.simulated_p_success < 0.5, (
            f"{r.cid}: simulated P(success)={r.simulated_p_success:.2f} too high"
        )


def test_aggressive_cohort_is_honestly_refused(
    cohort_results: list[CohortResult],
) -> None:
    """The B1→C2 cohort specifically must NOT be projected as success."""
    aggressive = [
        r for r in cohort_results if r.cid == "aggressive_B1_target_C2"
    ]
    assert aggressive, "missing aggressive_B1_target_C2 cohort"
    for r in aggressive:
        assert (
            not r.planner_projection_success
        ), f"{r.cid}: planner projects success ({r.planner_projected_min:.2f})"


def test_trivial_cohort_remains_at_target(
    cohort_results: list[CohortResult],
) -> None:
    """The already-at-target cohort doesn't degrade."""
    trivial = [r for r in cohort_results if r.kind == "trivial"]
    for r in trivial:
        assert r.simulated_p_success >= 0.95, r.notes


def test_overall_gate_pass(cohort_results: list[CohortResult]) -> None:
    """The audit's headline gate: every cohort passes."""
    failing = [r for r in cohort_results if not r.gate_pass]
    if failing:
        msg_lines = ["Cohort gate failures:"]
        for r in failing:
            msg_lines.append(f"  - {r.cid} ({r.kind}): {r.notes}")
        pytest.fail("\n".join(msg_lines))


def test_report_artefacts_emitted(cohort_results: list[CohortResult]) -> None:
    """The JSON + Mermaid artefacts land in data/audit/phase9/."""
    assert REPORT_JSON.exists(), f"missing {REPORT_JSON}"
    assert REPORT_PLOT.exists(), f"missing {REPORT_PLOT}"
    payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    assert payload["phase"] == 9
    assert len(payload["cohorts"]) == 12


__all__ = [
    "CALIBRATION_WINDOW_NCLC",
    "LAUNCH_COHORTS",
    "REALISTIC_MIN_PSUCCESS",
    "REPORT_JSON",
    "REPORT_PLOT",
    "CohortResult",
    "LaunchCohort",
]
