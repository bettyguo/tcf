"""Release-time κ evaluation against a held-out expert set.

Usage:
    python scripts/eval_kappa.py \
        --module EE \
        --rubric-version ee.v1 \
        --calibrator data/calibration/ee.v1.json \
        --holdout data/calibration/ee.v1.holdout.jsonl

Emits a JSON κ table to stdout and a markdown summary alongside the
holdout file. ADR-038: every release MUST run this and ship the κ
table in the release notes.

Exits non-zero when the published κ falls below 0.55 unless
`--allow-experimental` is set (which adds the "experimental" badge
flag to the JSON output).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from tcf_accel_ml.scoring.calibrate.calibrator import RubricCalibrator
from tcf_accel_ml.scoring.calibrate.kappa import (
    mae,
    pearson_r,
    quadratic_weighted_kappa,
)
from tcf_accel_ml.scoring.ee.score import EEScorer
from tcf_accel_ml.scoring.eo.score import EOScorer

_KAPPA_GATE: float = 0.55
_KAPPA_TARGET: float = 0.65


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _eval_ee(
    rows: list[dict[str, Any]],
    calibrator: RubricCalibrator | None,
    rubric_version: str,
) -> dict[str, Any]:
    scorer = EEScorer(calibrator=calibrator, rubric_version=rubric_version)
    pred_per_dim: dict[str, list[int]] = {}
    expert_per_dim: dict[str, list[int]] = {}
    total_pred: list[float] = []
    total_expert: list[float] = []

    for row in rows:
        result = scorer.score(
            text=row["text"],
            prompt=row.get("prompt", ""),
            task_number=int(row["task_number"]),
            target_word_count_range=tuple(row["target_word_count_range"]),  # type: ignore[arg-type]
            required_canadian_context=bool(row.get("required_canadian_context", False)),
        )
        rb = result.rubric
        pred = {
            "task_completion": rb.task_completion,
            "coherence_cohesion": rb.coherence_cohesion,
            "lexical_range": rb.lexical_range,
            "grammatical_accuracy": rb.grammatical_accuracy,
            "register_appropriateness": rb.register_appropriateness,
            "canadian_context_integration": rb.canadian_context_integration or 0,
        }
        expert = row["expert_scores"]
        for dim, score in pred.items():
            pred_per_dim.setdefault(dim, []).append(int(score))
            expert_per_dim.setdefault(dim, []).append(int(expert.get(dim, 0)))
        total_pred.append(rb.total_20)
        total_expert.append(float(row.get("expert_total_20", _expert_total_20(expert))))

    return _summarize(pred_per_dim, expert_per_dim, total_pred, total_expert, rows)


def _eval_eo(
    rows: list[dict[str, Any]],
    calibrator: RubricCalibrator | None,
    rubric_version: str,
) -> dict[str, Any]:
    scorer = EOScorer(calibrator=calibrator, rubric_version=rubric_version)
    pred_per_dim: dict[str, list[int]] = {}
    expert_per_dim: dict[str, list[int]] = {}
    total_pred: list[float] = []
    total_expert: list[float] = []

    for row in rows:
        result = scorer.score(
            transcript=row.get("transcript", ""),
            prompt=row.get("prompt", ""),
            task_number=int(row["task_number"]),
            duration_s=float(row.get("duration_s", 0.0)),
            asr_mean_confidence=float(row.get("asr_mean_confidence", 0.0)),
            pronunciation_signal=None,
        )
        rb = result.rubric
        pred = {
            "task_completion": rb.task_completion,
            "fluency_pace": rb.fluency_pace,
            "pronunciation_prosody": rb.pronunciation_prosody,
            "lexical_range": rb.lexical_range,
            "grammatical_accuracy": rb.grammatical_accuracy,
            "interaction_responsiveness": rb.interaction_responsiveness,
        }
        expert = row["expert_scores"]
        for dim, score in pred.items():
            pred_per_dim.setdefault(dim, []).append(int(score))
            expert_per_dim.setdefault(dim, []).append(int(expert.get(dim, 0)))
        total_pred.append(rb.total_20)
        total_expert.append(float(row.get("expert_total_20", _expert_total_20(expert, eo=True))))

    return _summarize(pred_per_dim, expert_per_dim, total_pred, total_expert, rows)


def _expert_total_20(expert: dict[str, int], *, eo: bool = False) -> float:
    if eo:
        s = sum(int(expert.get(k, 0)) for k in (
            "task_completion", "fluency_pace", "pronunciation_prosody",
            "lexical_range", "grammatical_accuracy", "interaction_responsiveness",
        ))
        return round(s * 2.0 / 3.0)
    s = sum(int(expert.get(k, 0)) for k in (
        "task_completion", "coherence_cohesion", "lexical_range",
        "grammatical_accuracy", "register_appropriateness",
    ))
    return round(s * 4.0 / 5.0)


def _summarize(
    pred_per_dim: dict[str, list[int]],
    expert_per_dim: dict[str, list[int]],
    total_pred: Sequence[float],
    total_expert: Sequence[float],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    per_dim_report: list[dict[str, Any]] = []
    kappas: list[float] = []
    for dim, pred in pred_per_dim.items():
        expert = expert_per_dim[dim]
        k = quadratic_weighted_kappa(
            rater_a=pred, rater_b=expert, min_rating=0, max_rating=5,
        )
        per_dim_report.append({
            "dimension": dim,
            "kappa": k,
            "pearson_r": pearson_r(pred, expert),
            "mae": mae(pred, expert),
            "n": len(pred),
        })
        kappas.append(k)
    overall_kappa = sum(kappas) / len(kappas) if kappas else 0.0
    rater_kinds = {r.get("rater_kind", "silver") for r in rows}
    label = "gold" if rater_kinds == {"gold"} else "silver"
    return {
        "rater_label": label,
        "overall_kappa": overall_kappa,
        "per_dimension": per_dim_report,
        "total_20_mae": mae(list(total_pred), list(total_expert)),
        "total_20_pearson_r": pearson_r(list(total_pred), list(total_expert)),
        "n_rows": len(rows),
    }


def _write_markdown(report: dict[str, Any], target: Path) -> None:
    lines = [
        "# κ evaluation",
        "",
        f"- Rater label: `{report['rater_label']}`",
        f"- Overall κ (mean across dims): `{report['overall_kappa']:.3f}`",
        f"- MAE on total_20: `{report['total_20_mae']:.3f}`",
        f"- Pearson r on total_20: `{report['total_20_pearson_r']:.3f}`",
        f"- Rows: `{report['n_rows']}`",
        "",
        "| Dimension | κ | r | MAE | n |",
        "|---|---|---|---|---|",
    ]
    for row in report["per_dimension"]:
        lines.append(
            f"| `{row['dimension']}` | {row['kappa']:.3f} | "
            f"{row['pearson_r']:.3f} | {row['mae']:.3f} | {row['n']} |"
        )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Evaluate κ on a held-out expert set.")
    p.add_argument("--module", choices=["EE", "EO"], required=True)
    p.add_argument("--rubric-version", default="ee.v1")
    p.add_argument("--calibrator", type=Path, default=None)
    p.add_argument("--holdout", type=Path, required=True)
    p.add_argument("--allow-experimental", action="store_true")
    args = p.parse_args(argv)

    if not args.holdout.exists():
        print(f"holdout not found: {args.holdout}", file=sys.stderr)
        return 2
    rows = _read_jsonl(args.holdout)
    if not rows:
        print("empty holdout", file=sys.stderr)
        return 2

    calibrator: RubricCalibrator | None = None
    if args.calibrator and args.calibrator.exists():
        calibrator = RubricCalibrator.load(args.calibrator)

    if args.module == "EE":
        report = _eval_ee(rows, calibrator, args.rubric_version)
    else:
        report = _eval_eo(rows, calibrator, args.rubric_version)

    report["target_kappa"] = _KAPPA_TARGET
    report["experimental"] = report["overall_kappa"] < _KAPPA_GATE
    if report["experimental"] and not args.allow_experimental:
        print(json.dumps(report, indent=2))
        print(
            f"FAIL: overall κ {report['overall_kappa']:.3f} < gate {_KAPPA_GATE} "
            f"and --allow-experimental not set",
            file=sys.stderr,
        )
        return 1

    _write_markdown(report, args.holdout.with_suffix(".kappa.md"))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
