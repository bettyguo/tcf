"""Cohen's quadratic-weighted κ + MAE + Pearson r.

Pure-Python; no numpy dependency. Used by the calibrator's LOO-CV,
the release-time κ evaluator (`scripts/eval_kappa.py`), and the
Phase 7 audit tests.

Quadratic weights penalise larger disagreements more than smaller ones,
which is the standard choice for ordinal rubric scores (0–5).
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def quadratic_weighted_kappa(
    *,
    rater_a: Sequence[int],
    rater_b: Sequence[int],
    min_rating: int | None = None,
    max_rating: int | None = None,
) -> float:
    """Cohen's quadratic-weighted κ.

    Returns 1.0 when raters agree perfectly, ~0.0 when agreement is at
    chance, negative when worse than chance.

    Example:
        >>> abs(quadratic_weighted_kappa(rater_a=[3, 4, 5], rater_b=[3, 4, 5]) - 1.0) < 1e-9
        True
        >>> -1.0 <= quadratic_weighted_kappa(
        ...     rater_a=[3, 4, 5, 3, 4],
        ...     rater_b=[5, 3, 4, 4, 5],
        ... ) <= 1.0
        True

    Complexity: O(n + r^2) where r is the rating range size.
    """
    if len(rater_a) != len(rater_b):
        raise ValueError("rater_a and rater_b must have the same length")
    if not rater_a:
        return 0.0

    if min_rating is None:
        min_rating = min(min(rater_a), min(rater_b))
    if max_rating is None:
        max_rating = max(max(rater_a), max(rater_b))

    n_ratings = max_rating - min_rating + 1
    if n_ratings <= 1:
        return 1.0 if list(rater_a) == list(rater_b) else 0.0

    # Confusion matrix.
    conf = [[0 for _ in range(n_ratings)] for _ in range(n_ratings)]
    for a, b in zip(rater_a, rater_b, strict=True):
        conf[a - min_rating][b - min_rating] += 1

    # Histograms.
    hist_a = [sum(conf[i]) for i in range(n_ratings)]
    hist_b = [sum(conf[i][j] for i in range(n_ratings)) for j in range(n_ratings)]

    n = len(rater_a)
    num = 0.0
    den = 0.0
    for i in range(n_ratings):
        for j in range(n_ratings):
            w = ((i - j) ** 2) / ((n_ratings - 1) ** 2)
            observed = conf[i][j]
            expected = (hist_a[i] * hist_b[j]) / n
            num += w * observed
            den += w * expected
    if den == 0.0:
        return 1.0
    return 1.0 - (num / den)


def mae(predictions: Sequence[float], targets: Sequence[float]) -> float:
    """Mean absolute error.

    Example:
        >>> mae([1.0, 2.0, 3.0], [1.5, 2.5, 3.5])
        0.5
    """
    if len(predictions) != len(targets):
        raise ValueError("length mismatch")
    if not predictions:
        return 0.0
    return sum(abs(p - t) for p, t in zip(predictions, targets, strict=True)) / len(predictions)


def pearson_r(predictions: Sequence[float], targets: Sequence[float]) -> float:
    """Pearson correlation coefficient.

    Returns 0.0 when either input is constant.

    Example:
        >>> abs(pearson_r([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) - 1.0) < 1e-9
        True
    """
    if len(predictions) != len(targets):
        raise ValueError("length mismatch")
    n = len(predictions)
    if n == 0:
        return 0.0
    mean_p = sum(predictions) / n
    mean_t = sum(targets) / n
    num = 0.0
    var_p = 0.0
    var_t = 0.0
    for p, t in zip(predictions, targets, strict=True):
        dp = p - mean_p
        dt = t - mean_t
        num += dp * dt
        var_p += dp * dp
        var_t += dt * dt
    den = math.sqrt(var_p * var_t)
    if den == 0.0:
        return 0.0
    return num / den


__all__ = ["mae", "pearson_r", "quadratic_weighted_kappa"]
