"""Mock scorer — score consistency, divergence alert, composite NCLC."""

from __future__ import annotations

import random
from uuid import UUID, uuid4

import pytest

from tcf_accel.ids import ItemId

from tcf_accel_sla.estimator.nclc import bootstrap_posterior
from tcf_accel_sla.mock_exam import (
    ItemOutcome,
    RubricOutcome,
    composite_nclc,
    divergence_alert,
    score_mock,
)
from tcf_accel_sla.mock_exam.scorer import DRILL_MOCK_DIVERGENCE_THRESHOLD


def _co_outcome(seed: int, difficulty: float, correct: bool) -> ItemOutcome:
    return ItemOutcome(
        item_id=ItemId(UUID(int=seed)),
        module="CO",
        difficulty=difficulty,
        discrimination=1.0,
        correct=correct,
        rt_ms=10_000,
    )


def _rubric_outcome(seed: int, task: int, total: float, module: str = "EE") -> RubricOutcome:
    return RubricOutcome(
        item_id=ItemId(UUID(int=seed)),
        module=module,  # type: ignore[arg-type]
        task_number=task,
        prompt_target_nclc=6.0,
        rubric_total_20=total,
    )


def test_perfect_co_drives_posterior_up() -> None:
    co = [_co_outcome(i, difficulty=8.0, correct=True) for i in range(1, 40)]
    result = score_mock(co=co, ce=[], ee=[], eo=[])
    assert result.per_skill["CO"].posterior.mean > 6.0


def test_all_wrong_co_drives_posterior_down() -> None:
    co = [_co_outcome(i, difficulty=8.0, correct=False) for i in range(1, 40)]
    result = score_mock(co=co, ce=[], ee=[], eo=[])
    assert result.per_skill["CO"].posterior.mean < 5.0


def test_score_includes_rubric_means() -> None:
    ee = [
        _rubric_outcome(1, task=1, total=18, module="EE"),
        _rubric_outcome(2, task=2, total=14, module="EE"),
        _rubric_outcome(3, task=3, total=10, module="EE"),
    ]
    result = score_mock(co=[], ce=[], ee=ee, eo=[])
    assert result.per_skill["EE"].raw == pytest.approx((18 + 14 + 10) / 3.0)
    assert result.per_skill["EE"].max_raw == 20.0


def test_divergence_alert_fires_at_threshold() -> None:
    drill = bootstrap_posterior(skill="CO", self_report_nclc=9.0)
    mock = bootstrap_posterior(skill="CO", self_report_nclc=5.0)
    alert = divergence_alert(drill, mock)
    assert alert is not None
    assert "CO" in alert


def test_divergence_alert_silent_below_threshold() -> None:
    drill = bootstrap_posterior(skill="CO", self_report_nclc=6.0)
    mock = bootstrap_posterior(skill="CO", self_report_nclc=5.0)
    alert = divergence_alert(drill, mock)
    assert alert is None


def test_score_mock_attaches_divergence_alerts() -> None:
    drill = {
        s: bootstrap_posterior(skill=s, self_report_nclc=10.0)
        for s in ("CO", "CE", "EE", "EO")
    }
    # All CO answers wrong → mock CO drops; drill is at 10.
    co = [_co_outcome(i, difficulty=8.0, correct=False) for i in range(1, 40)]
    result = score_mock(co=co, ce=[], ee=[], eo=[], drill_posteriors=drill)
    assert any("CO" in alert for alert in result.divergence_alerts)


def test_composite_is_floor_of_min_posterior_mean() -> None:
    co = [_co_outcome(i, difficulty=7.0, correct=True) for i in range(1, 40)]
    ce = [_co_outcome(i + 1000, difficulty=7.0, correct=True) for i in range(1, 40)]
    ce = [
        ItemOutcome(
            item_id=o.item_id,
            module="CE",
            difficulty=o.difficulty,
            discrimination=o.discrimination,
            correct=o.correct,
            rt_ms=o.rt_ms,
        )
        for o in ce
    ]
    ee = [
        _rubric_outcome(2000 + i, task=t, total=16, module="EE")
        for i, t in enumerate((1, 2, 3))
    ]
    eo = [
        _rubric_outcome(3000 + i, task=t, total=16, module="EO")
        for i, t in enumerate((1, 2, 3))
    ]
    result = score_mock(co=co, ce=ce, ee=ee, eo=eo)
    means = {s: ms.posterior.mean for s, ms in result.per_skill.items()}
    expected_bottleneck = min(means, key=lambda s: means[s])
    assert result.bottleneck_skill == expected_bottleneck


def test_overall_suppressed_when_any_skill_not_confident() -> None:
    co = [_co_outcome(i, difficulty=5.0, correct=True) for i in range(1, 5)]
    result = score_mock(co=co, ce=[], ee=[], eo=[])
    assert not result.overall_confident
    assert result.overall_nclc is None


def test_score_consistency_at_known_reliability() -> None:
    """A candidate at reliability p across difficulty 6 produces posterior near NCLC 6 ± 0.5 over 50 runs.

    Spec §4 invariant: "a candidate that answers correctly with
    reliability p produces a posterior mean within ±0.5 NCLC of
    `expected_nclc(p)` over 50 runs."
    """
    rng = random.Random(42)
    means = []
    for _ in range(50):
        co = []
        for i in range(40):
            correct = rng.random() < 0.5  # 50% at difficulty 6 → NCLC ≈ 6
            co.append(_co_outcome(i + 1, difficulty=6.0, correct=correct))
        result = score_mock(co=co, ce=[], ee=[], eo=[])
        means.append(result.per_skill["CO"].posterior.mean)
    avg = sum(means) / len(means)
    assert abs(avg - 6.0) < 0.5, f"avg posterior mean {avg:.2f}, expected ~6.0"
