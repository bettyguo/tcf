"""Calibration layer tests (Phase 7).

Covers `Ridge`, `RubricCalibrator`, and the κ/MAE/Pearson metrics.
"""

from __future__ import annotations

from pathlib import Path

from tcf_accel_ml.scoring.calibrate.calibrator import RubricCalibrator
from tcf_accel_ml.scoring.calibrate.kappa import (
    mae,
    pearson_r,
    quadratic_weighted_kappa,
)
from tcf_accel_ml.scoring.calibrate.ridge import Ridge


# ─── Ridge ───────────────────────────────────────────────────────


def test_ridge_recovers_linear_relation() -> None:
    r = Ridge(alpha=0.001)
    X = [[float(i)] for i in range(10)]
    y = [2.0 * i + 1.0 for i in range(10)]
    r.fit(X, y)
    # Predict on a held-out point should be close to truth.
    assert abs(r.predict([5.0]) - 11.0) < 0.1


def test_ridge_handles_multi_feature() -> None:
    r = Ridge(alpha=0.001)
    X = [
        [1.0, 2.0],
        [2.0, 1.0],
        [3.0, 5.0],
        [0.0, 7.0],
        [4.0, 1.5],
        [2.5, 3.0],
    ]
    # y = 2*x0 + 0.5*x1 + 1
    y = [2.0 * x[0] + 0.5 * x[1] + 1.0 for x in X]
    r.fit(X, y)
    pred = r.predict([3.0, 4.0])
    assert abs(pred - 9.0) < 0.3


def test_ridge_serializes_and_deserializes() -> None:
    r = Ridge(alpha=0.5)
    r.fit([[1.0], [2.0], [3.0]], [2.0, 4.0, 6.0])
    blob = r.serialize()
    r2 = Ridge.deserialize(blob)
    assert r.weights == r2.weights
    assert r.alpha == r2.alpha


# ─── κ + MAE + Pearson ──────────────────────────────────────────


def test_kappa_perfect_agreement_is_one() -> None:
    assert abs(quadratic_weighted_kappa(
        rater_a=[3, 4, 5, 2, 1], rater_b=[3, 4, 5, 2, 1],
        min_rating=0, max_rating=5,
    ) - 1.0) < 1e-9


def test_kappa_within_range() -> None:
    k = quadratic_weighted_kappa(
        rater_a=[3, 4, 5, 2, 1, 3],
        rater_b=[5, 1, 4, 5, 3, 2],
        min_rating=0, max_rating=5,
    )
    assert -1.0 <= k <= 1.0


def test_kappa_off_by_one_better_than_off_by_three() -> None:
    near = quadratic_weighted_kappa(
        rater_a=[1, 2, 3, 4, 5],
        rater_b=[2, 3, 4, 5, 4],
        min_rating=0, max_rating=5,
    )
    far = quadratic_weighted_kappa(
        rater_a=[1, 2, 3, 4, 5],
        rater_b=[4, 5, 0, 1, 2],
        min_rating=0, max_rating=5,
    )
    assert near > far


def test_mae_zero_for_identical() -> None:
    assert mae([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0


def test_pearson_r_for_perfectly_linear() -> None:
    assert abs(pearson_r([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0]) - 1.0) < 1e-9


def test_pearson_r_zero_for_constant() -> None:
    # constant predictions → 0 (no variance).
    assert pearson_r([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) == 0.0


# ─── RubricCalibrator ───────────────────────────────────────────


def test_calibrator_fit_predict_round_trip() -> None:
    dims = ["task_completion", "lexical_range"]
    cal = RubricCalibrator(rubric_version="ee.v1", dimensions=dims, alpha=0.1)
    # Synthetic: expert = llm * 0.9 + features[0] * 0.05
    features = [[float(i)] for i in range(20)]
    llm = {dim: [float(i % 5) for i in range(20)] for dim in dims}
    expert = {
        dim: [
            llm[dim][i] * 0.9 + features[i][0] * 0.05
            for i in range(20)
        ]
        for dim in dims
    }
    reports = cal.fit(
        features_per_row=features,
        llm_scores_per_row=llm,
        expert_scores_per_row=expert,
    )
    assert len(reports) == 2
    pred = cal.predict(features=[10.0], llm_scores={"task_completion": 3.0, "lexical_range": 2.0})
    assert "task_completion" in pred
    assert "lexical_range" in pred


def test_calibrator_serializes_to_json(tmp_path: Path) -> None:
    cal = RubricCalibrator(
        rubric_version="ee.v1",
        dimensions=["task_completion"],
        alpha=0.1,
    )
    cal.fit(
        features_per_row=[[1.0], [2.0], [3.0], [4.0]],
        llm_scores_per_row={"task_completion": [1.0, 2.0, 3.0, 4.0]},
        expert_scores_per_row={"task_completion": [1.5, 2.5, 3.5, 4.5]},
    )
    path = tmp_path / "ee.v1.json"
    cal.save(path)
    assert path.exists()
    loaded = RubricCalibrator.load(path)
    assert loaded.rubric_version == cal.rubric_version
    assert loaded.training_set_hash == cal.training_set_hash
    a = cal.predict(features=[2.5], llm_scores={"task_completion": 2.5})
    b = loaded.predict(features=[2.5], llm_scores={"task_completion": 2.5})
    assert abs(a["task_completion"] - b["task_completion"]) < 1e-6


def test_calibrator_training_set_hash_is_deterministic() -> None:
    cal_a = RubricCalibrator(rubric_version="ee.v1", dimensions=["task_completion"])
    cal_b = RubricCalibrator(rubric_version="ee.v1", dimensions=["task_completion"])
    payload = {
        "features_per_row": [[1.0], [2.0]],
        "llm_scores_per_row": {"task_completion": [1.0, 2.0]},
        "expert_scores_per_row": {"task_completion": [1.0, 2.0]},
    }
    cal_a.fit(**payload)
    cal_b.fit(**payload)
    assert cal_a.training_set_hash == cal_b.training_set_hash
