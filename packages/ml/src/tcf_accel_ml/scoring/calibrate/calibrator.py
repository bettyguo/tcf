"""`RubricCalibrator` — per-dimension Ridge over (features, llm_score).

The calibrator fits a small Ridge model per rubric dimension:
    expert_score = w_features · features + w_llm · llm_score + bias

Persisted as JSON (no joblib / pickle) so the file is human-auditable
and forward-compatible. The training-set hash is included so the audit
can verify a deployed calibrator matches the dataset it claims.

When no calibrator is available, callers should fall back to the
uncalibrated identity path (LLM scores pass-through, `confident=False`).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from tcf_accel_ml.scoring.calibrate.kappa import (
    mae,
    pearson_r,
    quadratic_weighted_kappa,
)
from tcf_accel_ml.scoring.calibrate.ridge import Ridge


@dataclass
class DimensionFitReport:
    """Per-dimension metrics emitted after `fit()`.

    Used by `scripts/calibrate.py` for the release-time κ table and
    by the audit tests.
    """

    dimension: str
    kappa: float
    pearson_r: float
    mae: float
    n_rows: int


@dataclass
class RubricCalibrator:
    """Per-dimension Ridge over (features, LLM score) → expert score.

    Persisted as JSON. Versioned by `(rubric_version, training_set_hash)`.
    """

    rubric_version: str
    dimensions: list[str]
    alpha: float = 1.0
    models: dict[str, Ridge] = field(default_factory=dict)
    training_set_hash: str = ""
    reports: list[DimensionFitReport] = field(default_factory=list)

    def fit(
        self,
        *,
        features_per_row: list[list[float]],
        llm_scores_per_row: dict[str, list[float]],
        expert_scores_per_row: dict[str, list[float]],
    ) -> list[DimensionFitReport]:
        """Fit one Ridge per dimension. Returns per-dimension fit reports.

        Each dimension's feature vector is the supplied feature vector
        concatenated with that dimension's LLM score. This keeps the
        calibrator capable of learning either an "LLM-dominated" or a
        "features-dominated" combination per dimension.
        """
        self.models = {}
        self.reports = []
        rows = features_per_row
        n = len(rows)
        if n == 0:
            return self.reports

        self.training_set_hash = self._hash_training_set(
            features_per_row, llm_scores_per_row, expert_scores_per_row,
        )

        for dim in self.dimensions:
            llm = llm_scores_per_row.get(dim, [])
            expert = expert_scores_per_row.get(dim, [])
            if len(llm) != n or len(expert) != n:
                continue
            X = [features + [llm[i]] for i, features in enumerate(rows)]
            r = Ridge(alpha=self.alpha)
            r.fit(X, expert)
            self.models[dim] = r

            preds = [r.predict(x) for x in X]
            # Quadratic-weighted κ wants integer scores; round and clamp.
            preds_int = [max(0, min(5, int(round(p)))) for p in preds]
            expert_int = [max(0, min(5, int(round(e)))) for e in expert]
            self.reports.append(
                DimensionFitReport(
                    dimension=dim,
                    kappa=quadratic_weighted_kappa(
                        rater_a=preds_int, rater_b=expert_int,
                        min_rating=0, max_rating=5,
                    ),
                    pearson_r=pearson_r(preds, expert),
                    mae=mae(preds, expert),
                    n_rows=n,
                )
            )
        return self.reports

    def predict(
        self,
        *,
        features: list[float],
        llm_scores: dict[str, float],
    ) -> dict[str, float]:
        """Predict the expert score for each dimension.

        Returns a partial dict when some dimensions are uncalibrated.
        """
        out: dict[str, float] = {}
        for dim, model in self.models.items():
            llm = llm_scores.get(dim, 0.0)
            x = list(features) + [float(llm)]
            out[dim] = model.predict(x)
        return out

    def has(self, dim: str) -> bool:
        return dim in self.models

    # ─── Persistence ─────────────────────────────────────────────

    def serialize(self) -> dict[str, object]:
        return {
            "schema_version": "phase7.v1",
            "rubric_version": self.rubric_version,
            "dimensions": list(self.dimensions),
            "alpha": self.alpha,
            "training_set_hash": self.training_set_hash,
            "models": {dim: m.serialize() for dim, m in self.models.items()},
            "reports": [
                {
                    "dimension": r.dimension,
                    "kappa": r.kappa,
                    "pearson_r": r.pearson_r,
                    "mae": r.mae,
                    "n_rows": r.n_rows,
                }
                for r in self.reports
            ],
        }

    @classmethod
    def deserialize(cls, blob: dict[str, object]) -> "RubricCalibrator":
        c = cls(
            rubric_version=str(blob["rubric_version"]),
            dimensions=list(blob["dimensions"]),  # type: ignore[arg-type]
            alpha=float(blob.get("alpha", 1.0)),  # type: ignore[arg-type]
        )
        c.training_set_hash = str(blob.get("training_set_hash", ""))
        c.models = {
            dim: Ridge.deserialize(m)
            for dim, m in (blob.get("models", {}) or {}).items()  # type: ignore[union-attr]
        }
        c.reports = [
            DimensionFitReport(**r)  # type: ignore[arg-type]
            for r in (blob.get("reports", []) or [])  # type: ignore[union-attr]
        ]
        return c

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.serialize(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "RubricCalibrator":
        return cls.deserialize(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _hash_training_set(
        features: list[list[float]],
        llm_scores: dict[str, list[float]],
        expert_scores: dict[str, list[float]],
    ) -> str:
        h = hashlib.sha256()
        blob = json.dumps(
            {
                "features": features,
                "llm_scores": llm_scores,
                "expert_scores": expert_scores,
            },
            sort_keys=True,
        )
        h.update(blob.encode("utf-8"))
        return h.hexdigest()


__all__ = ["DimensionFitReport", "RubricCalibrator"]
