"""Pure-Python Ridge regression.

Solves `(X^T X + α I) w = X^T y` via Gaussian elimination. No numpy
dependency — keeps the package importable in a clean venv. For the
Phase 7 use case (≤ 200 rows × ≤ 25 features) the closed-form solve
takes microseconds.

The model fits a bias term explicitly (the first weight). Inputs are
plain `list[list[float]]` / `list[float]`; no array library needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _matmul_t_self(X: list[list[float]]) -> list[list[float]]:
    """Return X^T X."""
    m = len(X)
    if m == 0:
        return []
    n = len(X[0])
    out = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            s = 0.0
            for row in X:
                s += row[i] * row[j]
            out[i][j] = s
            out[j][i] = s
    return out


def _matvec_t(X: list[list[float]], y: list[float]) -> list[float]:
    """Return X^T y."""
    m = len(X)
    n = len(X[0]) if m else 0
    out = [0.0] * n
    for i, row in enumerate(X):
        yi = y[i]
        for j in range(n):
            out[j] += row[j] * yi
    return out


def _gaussian_solve(A: list[list[float]], b: list[float]) -> list[float]:
    """In-place Gaussian elimination with partial pivoting.

    Returns the solution vector. Raises ValueError on a singular matrix.
    """
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        # Partial pivot.
        pivot_row = col
        pivot_val = abs(M[col][col])
        for r in range(col + 1, n):
            if abs(M[r][col]) > pivot_val:
                pivot_val = abs(M[r][col])
                pivot_row = r
        if pivot_val < 1e-12:
            raise ValueError("singular matrix in Ridge solve")
        if pivot_row != col:
            M[col], M[pivot_row] = M[pivot_row], M[col]
        # Eliminate.
        pivot = M[col][col]
        for r in range(n):
            if r != col and abs(M[r][col]) > 1e-15:
                factor = M[r][col] / pivot
                for c in range(col, n + 1):
                    M[r][c] -= factor * M[col][c]
    # Back-substitute (matrix is now diagonal).
    return [M[i][n] / M[i][i] for i in range(n)]


@dataclass
class Ridge:
    """Ridge regression with explicit bias term.

    Example:
        >>> r = Ridge()
        >>> r.fit([[1.0], [2.0], [3.0]], [2.0, 4.0, 6.0])
        >>> abs(r.predict([2.0]) - 4.0) < 0.5
        True

    Complexity: O(n_features^3) per fit + O(n_features) per predict.
    """

    alpha: float = 1.0
    weights: list[float] = field(default_factory=list)  # including bias as weights[0]

    def fit(self, X: list[list[float]], y: list[float]) -> None:
        if not X:
            self.weights = []
            return
        # Prepend bias column.
        X_aug = [[1.0, *row] for row in X]
        n_features = len(X_aug[0])
        XtX = _matmul_t_self(X_aug)
        for i in range(n_features):
            # Do not regularize the bias term.
            if i > 0:
                XtX[i][i] += self.alpha
        Xty = _matvec_t(X_aug, y)
        self.weights = _gaussian_solve(XtX, Xty)

    def predict(self, x: list[float]) -> float:
        if not self.weights:
            return 0.0
        # weights[0] is the bias; x has no bias prepended.
        s = self.weights[0]
        for i, xi in enumerate(x):
            s += self.weights[i + 1] * xi
        return s

    def serialize(self) -> dict[str, list[float] | float]:
        return {"alpha": self.alpha, "weights": list(self.weights)}

    @classmethod
    def deserialize(cls, blob: dict[str, list[float] | float]) -> "Ridge":
        r = cls(alpha=float(blob.get("alpha", 1.0)))
        r.weights = list(blob.get("weights", []))  # type: ignore[arg-type]
        return r


__all__ = ["Ridge"]
