"""Mock scoring — fresh per-skill posterior + divergence alert.

Per `phase6_design.md §6` and ADR-034:

- CO/CE outcomes are MCQ booleans; each folds into the posterior via
  the existing `update_with_mcq` machinery.
- EE/EO outcomes are `RubricOutcome` records; each folds in via
  `update_with_rubric`. The 3 task totals per module are averaged for
  the headline raw.
- The mock posterior is **fresh** (bootstrap_posterior) — independent
  of the drill posterior on purpose. The whole point of a mock is to
  measure exam-day performance without drill-history pollution.
- Composite = floor(min per-skill posterior mean) (TCF Canada
  bottleneck rule), suppressed entirely if any skill is not confident.
- Divergence alert: `|drill - mock| ≥ 2.0` per skill triggers a
  warning surfaced both in the report and the audit log.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Final

from tcf_accel.ids import ItemId
from tcf_accel.schemas.item import Module
from tcf_accel.schemas.scoring import SkillCode

from tcf_accel_sla.estimator.nclc import (
    NCLC_MAX,
    NCLC_MIN,
    SkillPosterior,
    bootstrap_posterior,
    update_with_mcq,
    update_with_rubric,
)

DRILL_MOCK_DIVERGENCE_THRESHOLD: Final[float] = 2.0


@dataclass(frozen=True)
class ItemOutcome:
    """One CO or CE item's outcome for the mock scorer."""

    item_id: ItemId
    module: Module        # "CO" or "CE"
    difficulty: float
    discrimination: float
    correct: bool
    rt_ms: int = 0


@dataclass(frozen=True)
class RubricOutcome:
    """One EE or EO task's outcome for the mock scorer."""

    item_id: ItemId
    module: Module        # "EE" or "EO"
    task_number: int
    prompt_target_nclc: float
    rubric_total_20: float


@dataclass(frozen=True)
class MockSkillScore:
    """Per-skill score result."""

    skill: SkillCode
    raw: float
    max_raw: float
    posterior: SkillPosterior
    n_items: int
    divergence_alert: str | None = None


@dataclass(frozen=True)
class ScoredMock:
    """The full scoring result."""

    per_skill: dict[SkillCode, MockSkillScore]
    overall_nclc: int | None        # None when not confident
    overall_confident: bool
    bottleneck_skill: SkillCode
    divergence_alerts: list[str] = field(default_factory=list)


def _score_co_or_ce(
    outcomes: Iterable[ItemOutcome],
    skill: SkillCode,
) -> MockSkillScore:
    """Bootstrap fresh posterior, fold every MCQ outcome in."""
    posterior = bootstrap_posterior(skill=skill, self_report_nclc=5.0)
    n = 0
    correct = 0
    for o in outcomes:
        posterior = update_with_mcq(
            posterior,
            item_difficulty=o.difficulty,
            discrimination=o.discrimination,
            correct=o.correct,
        )
        n += 1
        if o.correct:
            correct += 1
    return MockSkillScore(
        skill=skill,
        raw=float(correct),
        max_raw=float(n),
        posterior=posterior,
        n_items=n,
    )


def _score_ee_or_eo(
    outcomes: Iterable[RubricOutcome],
    skill: SkillCode,
) -> MockSkillScore:
    """Bootstrap fresh posterior, fold every rubric outcome in.

    Raw = mean of the rubric totals across tasks (so a learner who
    scored 18, 14, 12 on the three EE tasks has raw 14.67/20).
    """
    posterior = bootstrap_posterior(skill=skill, self_report_nclc=5.0)
    totals: list[float] = []
    for o in outcomes:
        posterior = update_with_rubric(
            posterior,
            rubric_total_20=o.rubric_total_20,
            prompt_target_nclc=o.prompt_target_nclc,
        )
        totals.append(o.rubric_total_20)
    n = len(totals)
    raw = sum(totals) / n if n else 0.0
    return MockSkillScore(
        skill=skill,
        raw=raw,
        max_raw=20.0,
        posterior=posterior,
        n_items=n,
    )


def divergence_alert(
    drill: SkillPosterior,
    mock: SkillPosterior,
    *,
    threshold: float = DRILL_MOCK_DIVERGENCE_THRESHOLD,
) -> str | None:
    """Return an alert string iff |drill.mean - mock.mean| ≥ threshold.

    ADR-034: a chronic divergence here usually indicates either drill
    overfitting (drill > mock) or a bank-calibration mismatch (mock >
    drill).
    """
    if drill.skill != mock.skill:
        msg = f"skill mismatch: drill={drill.skill} mock={mock.skill}"
        raise ValueError(msg)
    delta = mock.mean - drill.mean
    if abs(delta) < threshold:
        return None
    direction = "above" if delta > 0 else "below"
    return (
        f"{drill.skill}: mock posterior ({mock.mean:.1f}) is "
        f"{abs(delta):.1f} NCLC {direction} drill posterior "
        f"({drill.mean:.1f}); review for "
        f"{'bank calibration' if delta > 0 else 'drill overfitting'}."
    )


def composite_nclc(
    per_skill: Mapping[SkillCode, MockSkillScore],
) -> tuple[int | None, bool, SkillCode]:
    """Return (composite_nclc, confident, bottleneck_skill).

    Composite = floor of the minimum per-skill posterior mean (TCF
    Canada bottleneck rule). If *any* per-skill posterior has
    `confident=False`, composite is None and `confident` is False.
    """
    means = {s: score.posterior.mean for s, score in per_skill.items()}
    bottleneck = min(means, key=lambda s: means[s])
    confident = all(score.posterior.confident for score in per_skill.values())
    if not confident:
        return None, False, bottleneck
    composite = max(int(NCLC_MIN), min(int(NCLC_MAX), int(math.floor(means[bottleneck]))))
    return composite, True, bottleneck


def score_mock(
    *,
    co: Iterable[ItemOutcome],
    ce: Iterable[ItemOutcome],
    ee: Iterable[RubricOutcome],
    eo: Iterable[RubricOutcome],
    drill_posteriors: Mapping[SkillCode, SkillPosterior] | None = None,
) -> ScoredMock:
    """End-to-end mock scoring.

    `drill_posteriors` is optional; when supplied, the result includes
    per-skill divergence alerts.
    """
    per_skill: dict[SkillCode, MockSkillScore] = {
        "CO": _score_co_or_ce(co, "CO"),
        "CE": _score_co_or_ce(ce, "CE"),
        "EE": _score_ee_or_eo(ee, "EE"),
        "EO": _score_ee_or_eo(eo, "EO"),
    }

    alerts: list[str] = []
    if drill_posteriors is not None:
        for skill, score in per_skill.items():
            drill = drill_posteriors.get(skill)
            if drill is None:
                continue
            alert = divergence_alert(drill, score.posterior)
            if alert is not None:
                alerts.append(alert)
                per_skill[skill] = MockSkillScore(
                    skill=score.skill,
                    raw=score.raw,
                    max_raw=score.max_raw,
                    posterior=score.posterior,
                    n_items=score.n_items,
                    divergence_alert=alert,
                )

    composite, confident, bottleneck = composite_nclc(per_skill)
    return ScoredMock(
        per_skill=per_skill,
        overall_nclc=composite,
        overall_confident=confident,
        bottleneck_skill=bottleneck,
        divergence_alerts=alerts,
    )


__all__ = [
    "DRILL_MOCK_DIVERGENCE_THRESHOLD",
    "ItemOutcome",
    "MockSkillScore",
    "RubricOutcome",
    "ScoredMock",
    "composite_nclc",
    "divergence_alert",
    "score_mock",
]
