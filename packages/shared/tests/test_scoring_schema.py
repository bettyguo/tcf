"""Tests for `Score` and `NCLCEstimate` invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tcf_accel.schemas.scoring import NCLCEstimate, Score


def test_score_happy_path() -> None:
    s = Score(nclc=8, raw=510.0, ci_low=7, ci_high=9, n_observations=45, confident=True)
    assert s.nclc == 8
    assert s.ci_low == 7
    assert s.ci_high == 9


def test_ci_low_must_be_le_ci_high() -> None:
    with pytest.raises(ValueError, match="ci_low"):
        Score(nclc=8, raw=510.0, ci_low=9, ci_high=7, n_observations=45, confident=True)


def test_point_estimate_outside_ci_rejected() -> None:
    with pytest.raises(ValueError, match="within CI"):
        Score(nclc=10, raw=600.0, ci_low=7, ci_high=9, n_observations=45, confident=True)


def test_score_bounds() -> None:
    with pytest.raises(ValidationError):
        Score(nclc=0, raw=0, ci_low=1, ci_high=1, n_observations=0, confident=False)
    with pytest.raises(ValidationError):
        Score(nclc=13, raw=0, ci_low=12, ci_high=12, n_observations=0, confident=False)


def test_confident_false_is_allowed() -> None:
    # The schema doesn't enforce "show or hide"; it carries the flag.
    # The UI / API layer enforces "do not render as final" when confident=False.
    s = Score(nclc=6, raw=400.0, ci_low=4, ci_high=8, n_observations=5, confident=False)
    assert s.confident is False


def test_nclc_estimate_happy_path() -> None:
    est = NCLCEstimate(
        skill="EE",
        posterior_mean=8.4,
        ci_low=7,
        ci_high=9,
        confident=True,
        n_observations=60,
    )
    assert est.skill == "EE"


def test_nclc_estimate_mean_outside_ci_rejected() -> None:
    with pytest.raises(ValueError):
        NCLCEstimate(
            skill="EO",
            posterior_mean=10.5,
            ci_low=7,
            ci_high=9,
            confident=True,
            n_observations=60,
        )


def test_nclc_estimate_unknown_skill_rejected() -> None:
    with pytest.raises(ValidationError):
        NCLCEstimate(
            skill="XX",                              # type: ignore[arg-type]
            posterior_mean=8.0,
            ci_low=7,
            ci_high=9,
            confident=True,
            n_observations=60,
        )
