"""Bayesian NCLC estimator tests.

Calibration-shape invariants:
- A fresh prior is `confident=False`.
- The posterior mean moves toward the true value as observations accrue.
- Variance shrinks monotonically (or stays the same) with more observations.
- An NCLC-correct on a hard item shifts the mean more than the same
  correct on an easy item.
- The `confident` gate respects all three predicates from ADR-025.
- Projection to `NCLCEstimate` round-trips cleanly through the contract.
"""

from __future__ import annotations

import random

import pytest
from tcf_accel_sla.estimator.nclc import (
    CONFIDENT_MAX_VARIANCE,
    CONFIDENT_MIN_OBS,
    SkillPosterior,
    bootstrap_posterior,
    fisher_information,
    irt_p_correct,
    to_nclc_estimate,
    update_with_mcq,
    update_with_rubric,
)


def test_fresh_prior_is_not_confident() -> None:
    p = bootstrap_posterior(self_report_nclc=5.0)
    assert p.confident is False
    assert p.n_obs == 0


def test_irt_logistic_symmetric_at_difficulty_equals_theta() -> None:
    # P(correct | θ=b) = 0.5 by construction (logistic at zero).
    assert abs(irt_p_correct(5.0, 5.0, 1.0) - 0.5) < 1e-9


def test_fisher_information_peaks_at_difficulty_equals_theta() -> None:
    # 2PL info is maximized when p(1-p) is — i.e., at p=0.5 → θ=b.
    peak = fisher_information(5.0, 5.0, 1.0)
    off = fisher_information(5.0, 3.0, 1.0)
    assert peak > off


def test_correct_answer_raises_posterior_mean() -> None:
    p = bootstrap_posterior(self_report_nclc=5.0)
    p2 = update_with_mcq(p, item_difficulty=5.0, discrimination=1.0, correct=True)
    assert p2.mean > p.mean


def test_incorrect_answer_lowers_posterior_mean() -> None:
    p = bootstrap_posterior(self_report_nclc=5.0)
    p2 = update_with_mcq(p, item_difficulty=5.0, discrimination=1.0, correct=False)
    assert p2.mean < p.mean


def test_hard_item_correct_moves_mean_more_than_easy_item_correct() -> None:
    p = bootstrap_posterior(self_report_nclc=5.0)
    easy = update_with_mcq(p, item_difficulty=2.0, discrimination=1.0, correct=True)
    hard = update_with_mcq(p, item_difficulty=8.0, discrimination=1.0, correct=True)
    assert (hard.mean - p.mean) > (easy.mean - p.mean)


def test_variance_shrinks_with_more_observations() -> None:
    p = bootstrap_posterior(self_report_nclc=5.0)
    prev = p.variance
    for _ in range(20):
        p = update_with_mcq(p, item_difficulty=5.0, discrimination=1.0, correct=True)
        assert p.variance <= prev + 1e-6
        prev = p.variance


def test_n_obs_increments_per_update() -> None:
    p = bootstrap_posterior(self_report_nclc=5.0)
    for i in range(10):
        p = update_with_mcq(p, item_difficulty=5.0, discrimination=1.0, correct=True)
        assert p.n_obs == i + 1


def test_difficulty_spread_tracks_distinct_bands() -> None:
    p = bootstrap_posterior(self_report_nclc=5.0)
    for b in (3, 5, 7, 9):
        p = update_with_mcq(p, item_difficulty=float(b), discrimination=1.0, correct=True)
    assert p.difficulty_spread == 4


def test_confident_gate_requires_all_three_predicates() -> None:
    """ADR-025: n_obs >= 40 AND variance <= 0.4 AND spread >= 3."""
    # n_obs ok, variance ok, spread fails → not confident.
    p = SkillPosterior(
        skill="CO",
        mean=7.0,
        variance=0.2,
        n_obs=CONFIDENT_MIN_OBS,
        difficulty_bands_seen=frozenset({5}),
    )
    assert p.confident is False
    # n_obs ok, variance fails, spread ok → not confident.
    p2 = SkillPosterior(
        skill="CO",
        mean=7.0,
        variance=CONFIDENT_MAX_VARIANCE + 0.1,
        n_obs=CONFIDENT_MIN_OBS,
        difficulty_bands_seen=frozenset({3, 5, 7}),
    )
    assert p2.confident is False
    # n_obs fails, others ok → not confident.
    p3 = SkillPosterior(
        skill="CO",
        mean=7.0,
        variance=0.2,
        n_obs=CONFIDENT_MIN_OBS - 1,
        difficulty_bands_seen=frozenset({3, 5, 7}),
    )
    assert p3.confident is False
    # All three pass.
    p4 = SkillPosterior(
        skill="CO",
        mean=7.0,
        variance=0.2,
        n_obs=CONFIDENT_MIN_OBS,
        difficulty_bands_seen=frozenset({3, 5, 7}),
    )
    assert p4.confident is True


def test_to_nclc_estimate_satisfies_contract() -> None:
    p = SkillPosterior(
        skill="CO",
        mean=7.0,
        variance=0.2,
        n_obs=40,
        difficulty_bands_seen=frozenset({3, 5, 7}),
    )
    est = to_nclc_estimate(p)
    # Contract: ci_low <= posterior_mean <= ci_high (±0.5 tolerance).
    assert est.ci_low - 0.5 <= est.posterior_mean <= est.ci_high + 0.5
    assert est.confident is True
    assert est.n_observations == 40


def test_rubric_update_pushes_toward_observed_level() -> None:
    p = bootstrap_posterior(self_report_nclc=5.0, skill="EE")
    # Rubric 18/20 on a B2 (~NCLC 7) prompt → strong evidence of high ability.
    after = update_with_rubric(
        p, rubric_total_20=18.0, prompt_target_nclc=7.0,
    )
    assert after.mean > p.mean
    assert after.n_obs == 1


def test_invalid_self_report_rejected() -> None:
    with pytest.raises(ValueError):
        bootstrap_posterior(self_report_nclc=0.0)
    with pytest.raises(ValueError):
        bootstrap_posterior(self_report_nclc=13.0)


def test_calibration_recovers_known_true_level() -> None:
    """A learner with true NCLC 8 answers items in [4, 12] band IRT-style;
    posterior mean lands within ±0.8 of 8 after 40 items."""
    rng = random.Random(42)
    p = bootstrap_posterior(self_report_nclc=5.0)
    true_theta = 8.0
    for _ in range(50):
        difficulty = float(rng.randint(4, 11))
        prob = irt_p_correct(true_theta, difficulty, 1.0)
        correct = rng.random() < prob
        p = update_with_mcq(
            p, item_difficulty=difficulty, discrimination=1.0, correct=correct,
        )
    assert abs(p.mean - true_theta) < 0.8
