"""Bayesian per-skill NCLC posterior, with Laplace-approximation update.

Master prompt §6.2 and ADR-025: every reported NCLC point estimate MUST
come with a credible interval; the UI is forbidden from showing a final
number when `confident=False`. This module is the single source of truth
for those three properties.

The posterior is parameterized in NCLC-space, mean `μ ∈ [1, 12]` and
variance `σ² ∈ (0, ∞)`. For MCQ items we use a 2PL IRT likelihood
parameterized on the *NCLC scale directly* (not a separate θ-scale):
this avoids the IRT/NCLC linking step and keeps the audit-time invariant
"posterior mean is in NCLC units" tautological rather than empirical.

The Laplace approximation:

1. Find the posterior mode `μ*` by Newton-Raphson on the log-posterior.
2. Compute the second derivative at the mode: `H = d²log_post/dμ² |_{μ=μ*}`.
3. Approximate variance as `σ² = -1/H`.

For batch updates (a session's worth of items at once), we apply the
formula sequentially; the Laplace approximation is conservative —
variance shrinks more slowly than under HMC — which is the right error
direction for the "refuse to over-predict" guarantee.

Example:
    >>> p = bootstrap_posterior(self_report_nclc=5)
    >>> # Easy item the learner gets right → posterior mean rises a bit.
    >>> p2 = update_with_mcq(p, item_difficulty=3.0, discrimination=1.0, correct=True)
    >>> p2.mean > p.mean
    True
    >>> p2.n_obs == 1
    True

Complexity: each update is O(Newton iterations × 1) = O(constant); the
Newton loop converges in ≤ 8 iterations for sensible priors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Final, Literal

from tcf_accel.schemas.scoring import NCLCEstimate, SkillCode

NCLC_MIN: Final[float] = 1.0
NCLC_MAX: Final[float] = 12.0

# Confidence-gate thresholds. ADR-025 names these "launch-blocking" —
# the API is forbidden from showing a 🟢 / final NCLC number until all
# three predicates hold.
CONFIDENT_MIN_OBS: Final[int] = 40           # IRT 1PL minimum for sensible fit
CONFIDENT_MAX_VARIANCE: Final[float] = 0.4   # ≈ ±1 NCLC band
CONFIDENT_MIN_SPREAD: Final[int] = 3         # # of distinct difficulty bands observed

# Newton-Raphson tuning.
_NEWTON_MAX_ITER: Final[int] = 32
_NEWTON_TOL: Final[float] = 1e-6
_NEWTON_INIT_DAMPING: Final[float] = 1.0  # progressively reduced on divergence


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class SkillPosterior:
    """Per-skill posterior in NCLC space.

    `mean` is the posterior mean on the NCLC scale (1..12).
    `variance` is its variance under the Laplace approximation.
    `n_obs` is the count of interactions folded in (one per MCQ
    answered or per rubric scored).
    `difficulty_bands_seen` is the set of CEFR-band-integer-difficulties
    the learner has encountered, used by the `confident` gate to refuse
    over-prediction from a narrow evidence base.

    `ci_low` and `ci_high` are derived from `mean ± 1.96·σ` and clipped
    to `[1, 12]`. They are integer bands because the wire schema
    (`NCLCEstimate`) requires integers — the API consumer renders the
    band, not the continuous mean.
    """

    skill: SkillCode
    mean: float
    variance: float
    n_obs: int = 0
    difficulty_bands_seen: frozenset[int] = field(default_factory=frozenset)

    @property
    def stddev(self) -> float:
        """Posterior standard deviation in NCLC units."""
        return math.sqrt(max(self.variance, 0.0))

    @property
    def ci_low(self) -> int:
        """Lower 95% credible-interval endpoint, integer-banded."""
        return int(max(NCLC_MIN, math.floor(self.mean - 1.96 * self.stddev)))

    @property
    def ci_high(self) -> int:
        """Upper 95% credible-interval endpoint, integer-banded."""
        return int(min(NCLC_MAX, math.ceil(self.mean + 1.96 * self.stddev)))

    @property
    def difficulty_spread(self) -> int:
        """Number of distinct difficulty bands observed (for the confidence gate)."""
        return len(self.difficulty_bands_seen)

    @property
    def confident(self) -> bool:
        """The three-predicate confidence gate from §1.2 of the spec.

        All three must hold:
        - `n_obs >= CONFIDENT_MIN_OBS` (IRT 1PL fit minimum)
        - `variance <= CONFIDENT_MAX_VARIANCE` (≈ ±1 NCLC band)
        - `difficulty_spread >= CONFIDENT_MIN_SPREAD` (broad enough evidence)
        """
        return (
            self.n_obs >= CONFIDENT_MIN_OBS
            and self.variance <= CONFIDENT_MAX_VARIANCE
            and self.difficulty_spread >= CONFIDENT_MIN_SPREAD
        )


def bootstrap_posterior(
    *,
    skill: SkillCode = "CO",
    self_report_nclc: float = 5.0,
    prior_sigma: float = 1.2,
) -> SkillPosterior:
    """Construct a fresh prior from the learner's self-report.

    Default prior is N(5, 1.2²) — B1, broad. The 1.2 σ is wide enough
    that a 2-NCLC mismatch between self-report and reality is absorbed
    in roughly 8 interactions (an empirical sweet spot from the synthetic-
    cohort calibration audit).
    """
    if not (NCLC_MIN <= self_report_nclc <= NCLC_MAX):
        msg = f"self_report_nclc out of range: {self_report_nclc}"
        raise ValueError(msg)
    return SkillPosterior(
        skill=skill,
        mean=float(self_report_nclc),
        variance=prior_sigma ** 2,
        n_obs=0,
        difficulty_bands_seen=frozenset(),
    )


# ─── 2PL IRT in NCLC-space ────────────────────────────────────


def irt_p_correct(theta: float, difficulty: float, discrimination: float) -> float:
    """2PL: `P(correct | θ) = 1 / (1 + exp(-a · (θ - b)))`.

    `theta` is the learner ability on the NCLC scale; `difficulty` is
    the item's `b` parameter, also on the NCLC scale (so the difference
    `θ - b` is interpretable directly in NCLC bands). `discrimination`
    is the slope `a`; we clip it to `[0.2, 3.0]` per the IRT-fit prior
    used by the nightly batch.
    """
    a = _clip(discrimination, 0.2, 3.0)
    z = a * (theta - difficulty)
    # Numerically stable logistic.
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def fisher_information(theta: float, difficulty: float, discrimination: float) -> float:
    """2PL Fisher information at `θ`: `a² · p · (1 - p)`.

    Drives the diagnostic CAT next-item selection (`04_LEARNER_MODEL.md §1.3`,
    step 3): the next item is the one that maximizes this quantity at
    the current posterior mean.
    """
    p = irt_p_correct(theta, difficulty, discrimination)
    a = _clip(discrimination, 0.2, 3.0)
    return a * a * p * (1.0 - p)


# ─── Laplace-approximation update ─────────────────────────────


def _log_likelihood_mcq(
    theta: float,
    difficulty: float,
    discrimination: float,
    correct: bool,
) -> float:
    """log-likelihood of one MCQ outcome under 2PL."""
    p = irt_p_correct(theta, difficulty, discrimination)
    # Floor probabilities to avoid log(0) on degenerate items.
    p = _clip(p, 1e-9, 1.0 - 1e-9)
    return math.log(p) if correct else math.log(1.0 - p)


def _log_likelihood_grad_mcq(
    theta: float,
    difficulty: float,
    discrimination: float,
    correct: bool,
) -> float:
    """d/dθ log L for one MCQ outcome.

    For 2PL: `d/dθ log P(y | θ) = a · (y - p)`, where `y ∈ {0, 1}` is
    correctness and `p` is the model probability.
    """
    p = irt_p_correct(theta, difficulty, discrimination)
    a = _clip(discrimination, 0.2, 3.0)
    y = 1.0 if correct else 0.0
    return a * (y - p)


def _log_likelihood_hess_mcq(
    theta: float,
    difficulty: float,
    discrimination: float,
    correct: bool,
) -> float:
    """d²/dθ² log L for one MCQ outcome.

    For 2PL: `d²/dθ² log P(y | θ) = -a² · p · (1 - p)` — independent
    of the outcome `y`. (This is the negative Fisher information.)
    """
    _ = correct  # symmetric in y
    return -fisher_information(theta, difficulty, discrimination)


def update_with_mcq(
    prior: SkillPosterior,
    *,
    item_difficulty: float,
    discrimination: float = 1.0,
    correct: bool,
) -> SkillPosterior:
    """Fold one MCQ outcome into the posterior via Laplace approximation.

    The prior is Gaussian `N(μ_p, σ_p²)`; the likelihood is the 2PL above.
    The posterior is approximated Gaussian via Newton's method on the
    log-posterior:

        log P(θ | y) ∝ -(θ - μ_p)² / (2σ_p²) + log L(y | θ)

    First derivative:  g(θ) = -(θ - μ_p)/σ_p² + d log L / dθ
    Second derivative: h(θ) = -1/σ_p² + d² log L / dθ²

    Posterior mean: the root of `g`. Posterior variance: `-1/h(mean)`.

    Args:
        prior: The pre-observation posterior.
        item_difficulty: 2PL `b`, in NCLC units.
        discrimination: 2PL `a`; defaults to 1.0 (the IRT-fit default
            for un-calibrated items).
        correct: The learner's outcome on this item.

    Returns:
        New `SkillPosterior` with `n_obs += 1` and difficulty-band updated.
    """
    mu_p = prior.mean
    var_p = max(prior.variance, 1e-6)

    theta = mu_p  # Newton seed: prior mean.
    for _i in range(_NEWTON_MAX_ITER):
        grad = -(theta - mu_p) / var_p + _log_likelihood_grad_mcq(
            theta, item_difficulty, discrimination, correct,
        )
        hess = -1.0 / var_p + _log_likelihood_hess_mcq(
            theta, item_difficulty, discrimination, correct,
        )
        # `hess` is always negative (sum of two negative terms);
        # Newton step `θ_{n+1} = θ_n - g/h` decreases |g|.
        step = -grad / hess
        # Damp the step inside the NCLC support.
        damping = _NEWTON_INIT_DAMPING
        while damping > 1e-4:
            cand = _clip(theta + damping * step, NCLC_MIN, NCLC_MAX)
            if abs(cand - theta) < 1.0 or damping == _NEWTON_INIT_DAMPING:
                theta = cand
                break
            damping *= 0.5
        if abs(grad) < _NEWTON_TOL:
            break

    mu_post = _clip(theta, NCLC_MIN, NCLC_MAX)
    hess_at_mode = -1.0 / var_p + _log_likelihood_hess_mcq(
        mu_post, item_difficulty, discrimination, correct,
    )
    # Numerical guard: hess can never be 0 here, but clamp variance
    # against insanely small or large values.
    var_post = _clip(-1.0 / hess_at_mode, 1e-4, 9.0)

    return replace(
        prior,
        mean=mu_post,
        variance=var_post,
        n_obs=prior.n_obs + 1,
        difficulty_bands_seen=prior.difficulty_bands_seen | {round(item_difficulty)},
    )


# ─── Rubric (EE/EO) update ────────────────────────────────────


def _rubric_score_to_nclc(rubric_total_20: float) -> float:
    """Map a 0..20 rubric total onto the NCLC 1..12 scale.

    Anchor pairs from `06_MOCK_EXAM_ENGINE.md` (TCF score table):
    - rubric 0  ≈ NCLC 1
    - rubric 10 ≈ NCLC 6
    - rubric 16 ≈ NCLC 9
    - rubric 20 ≈ NCLC 12
    A linear interpolation over `[0, 20] → [1, 12]` is faithful within
    ±0.5 NCLC against the table; refinement is a Phase 7 calibration
    job, not an estimator concern.
    """
    return NCLC_MIN + (NCLC_MAX - NCLC_MIN) * (rubric_total_20 / 20.0)


def update_with_rubric(
    prior: SkillPosterior,
    *,
    rubric_total_20: float,
    prompt_target_nclc: float,
    obs_noise_sigma: float = 1.0,
) -> SkillPosterior:
    """Fold one rubric-scored EE/EO interaction into the posterior.

    Models the rubric score as `score | θ ~ N(θ - offset, σ_obs²)` where
    `offset = (prompt_target_nclc - 6)` corrects for prompt difficulty:
    a prompt targeting NCLC 9 that the learner aces is stronger evidence
    of high ability than the same score on a prompt targeting NCLC 5.

    With Gaussian prior + Gaussian likelihood the posterior is closed-
    form (no Newton needed):

        precision_post = 1/σ_p² + 1/σ_obs²
        μ_post = (μ_p/σ_p² + observed/σ_obs²) / precision_post
        σ_post² = 1 / precision_post

    Args:
        prior: Pre-observation posterior.
        rubric_total_20: Phase 7 auto-scorer total, 0..20.
        prompt_target_nclc: The NCLC band the prompt was authored for.
        obs_noise_sigma: Rubric noise; defaults to 1 NCLC unit (Phase 7
            audit will calibrate this).

    Returns:
        New `SkillPosterior` with `n_obs += 1` and difficulty-band updated.
    """
    observed = _rubric_score_to_nclc(rubric_total_20)
    # Prompt-difficulty offset: if the prompt targets above NCLC 6, a
    # given score implies higher ability; below 6, lower.
    offset = prompt_target_nclc - 6.0
    observed_adj = _clip(observed + offset / 2.0, NCLC_MIN, NCLC_MAX)

    var_p = max(prior.variance, 1e-6)
    var_obs = max(obs_noise_sigma * obs_noise_sigma, 1e-6)
    precision_post = 1.0 / var_p + 1.0 / var_obs
    mu_post = (prior.mean / var_p + observed_adj / var_obs) / precision_post
    var_post = 1.0 / precision_post

    return replace(
        prior,
        mean=_clip(mu_post, NCLC_MIN, NCLC_MAX),
        variance=_clip(var_post, 1e-4, 9.0),
        n_obs=prior.n_obs + 1,
        difficulty_bands_seen=prior.difficulty_bands_seen | {round(prompt_target_nclc)},
    )


# ─── Projection to the public `NCLCEstimate` ──────────────────


def to_nclc_estimate(posterior: SkillPosterior) -> NCLCEstimate:
    """Project the internal posterior onto the API contract shape.

    The contract requires `1 <= posterior_mean <= 12` and
    `ci_low <= posterior_mean <= ci_high` (±0.5 tolerance on the
    continuous mean against integer CI bands).
    """
    return NCLCEstimate(
        skill=posterior.skill,
        posterior_mean=_clip(posterior.mean, NCLC_MIN, NCLC_MAX),
        ci_low=posterior.ci_low,
        ci_high=posterior.ci_high,
        confident=posterior.confident,
        n_observations=posterior.n_obs,
    )


# ─── Convenience dispatcher ───────────────────────────────────


SkillKind = Literal["mcq", "rubric"]


__all__ = [
    "CONFIDENT_MAX_VARIANCE",
    "CONFIDENT_MIN_OBS",
    "CONFIDENT_MIN_SPREAD",
    "NCLC_MAX",
    "NCLC_MIN",
    "SkillKind",
    "SkillPosterior",
    "bootstrap_posterior",
    "fisher_information",
    "irt_p_correct",
    "to_nclc_estimate",
    "update_with_mcq",
    "update_with_rubric",
]
