"""Train a `RubricCalibrator` from a JSONL of expert ratings.

Usage:
    python scripts/calibrate.py \
        --module EE \
        --rubric-version ee.v1 \
        --input data/calibration/ee.v1.expert.jsonl \
        --output data/calibration/ee.v1.json

JSONL row schema (EE):
    {
      "id": "ee-0001",
      "rubric_version": "ee.v1",
      "task_number": 2,
      "text": "...",
      "prompt": "...",
      "target_word_count_range": [120, 150],
      "required_canadian_context": true,
      "rater_kind": "gold",         // "gold" or "silver"
      "expert_scores": {
          "task_completion": 4,
          "coherence_cohesion": 3,
          "lexical_range": 4,
          "grammatical_accuracy": 3,
          "register_appropriateness": 4,
          "canadian_context_integration": 3
      }
    }

Emits a per-dimension κ + Pearson r + MAE report next to the calibrator
JSON. The audit consumes the report; the route consumes the calibrator.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tcf_accel_ml.scoring.calibrate.calibrator import RubricCalibrator
from tcf_accel_ml.scoring.features.writing import extract_writing_features
from tcf_accel_ml.scoring.llm.critic import EE_RUBRIC_DIMENSIONS, EO_RUBRIC_DIMENSIONS
from tcf_accel_ml.scoring.llm.stub import LLMCriticStub


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _calibrate_ee(rows: list[dict[str, Any]], rubric_version: str) -> RubricCalibrator:
    critic = LLMCriticStub()
    features_per_row: list[list[float]] = []
    llm_scores_per_row: dict[str, list[float]] = {dim: [] for dim in EE_RUBRIC_DIMENSIONS}
    expert_scores_per_row: dict[str, list[float]] = {dim: [] for dim in EE_RUBRIC_DIMENSIONS}

    for row in rows:
        text = row["text"]
        prompt = row.get("prompt", "")
        task_number = int(row["task_number"])
        target_range = tuple(row["target_word_count_range"])
        required_canadian = bool(row.get("required_canadian_context", False))
        expert = row["expert_scores"]

        feats = extract_writing_features(text)
        features_per_row.append(feats.as_vector())

        critique = critic.critique_ee(
            prompt=prompt,
            text=text,
            rubric_version=rubric_version,
            task_number=task_number,
            target_word_count_range=target_range,  # type: ignore[arg-type]
            required_canadian_context=required_canadian,
        )
        for dim in EE_RUBRIC_DIMENSIONS:
            llm_scores_per_row[dim].append(float(critique.rubric_scores.get(dim, 0)))
            expert_scores_per_row[dim].append(float(expert.get(dim, 0)))

    cal = RubricCalibrator(
        rubric_version=rubric_version,
        dimensions=list(EE_RUBRIC_DIMENSIONS),
    )
    cal.fit(
        features_per_row=features_per_row,
        llm_scores_per_row=llm_scores_per_row,
        expert_scores_per_row=expert_scores_per_row,
    )
    return cal


def _calibrate_eo(rows: list[dict[str, Any]], rubric_version: str) -> RubricCalibrator:
    """EO calibration uses transcript-only features for v1.

    Pronunciation/prosody columns are out of scope for the calibrator;
    they are sourced from the Phase 5 pipeline at inference time.
    """
    critic = LLMCriticStub()
    features_per_row: list[list[float]] = []
    llm_scores_per_row: dict[str, list[float]] = {dim: [] for dim in EO_RUBRIC_DIMENSIONS}
    expert_scores_per_row: dict[str, list[float]] = {dim: [] for dim in EO_RUBRIC_DIMENSIONS}

    for row in rows:
        transcript = row.get("transcript", "")
        prompt = row.get("prompt", "")
        task_number = int(row["task_number"])
        duration_s = float(row.get("duration_s", 0.0))
        expert = row["expert_scores"]

        feats = extract_writing_features(transcript)
        features_per_row.append(feats.as_vector())

        critique = critic.critique_eo(
            prompt=prompt,
            transcript=transcript,
            rubric_version=rubric_version,
            task_number=task_number,
            duration_s=duration_s,
        )
        for dim in EO_RUBRIC_DIMENSIONS:
            llm_scores_per_row[dim].append(float(critique.rubric_scores.get(dim, 0)))
            expert_scores_per_row[dim].append(float(expert.get(dim, 0)))

    cal = RubricCalibrator(
        rubric_version=rubric_version,
        dimensions=list(EO_RUBRIC_DIMENSIONS),
    )
    cal.fit(
        features_per_row=features_per_row,
        llm_scores_per_row=llm_scores_per_row,
        expert_scores_per_row=expert_scores_per_row,
    )
    return cal


def _write_report(cal: RubricCalibrator, rater_kind: str, output: Path) -> Path:
    report_path = output.with_suffix(".report.md")
    lines = [
        f"# Calibration report — `{cal.rubric_version}`",
        "",
        f"- Training set hash: `{cal.training_set_hash[:16]}…`",
        f"- Rater kind: `{rater_kind}`",
        f"- α (Ridge): `{cal.alpha}`",
        "",
        "| Dimension | κ (QWK, 0–5) | Pearson r | MAE | n |",
        "|---|---|---|---|---|",
    ]
    for r in cal.reports:
        lines.append(
            f"| `{r.dimension}` | {r.kappa:.3f} | {r.pearson_r:.3f} | {r.mae:.3f} | {r.n_rows} |"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Train a rubric calibrator.")
    p.add_argument("--module", choices=["EE", "EO"], required=True)
    p.add_argument("--rubric-version", default="ee.v1")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)

    if not args.input.exists():
        print(f"input not found: {args.input}", file=sys.stderr)
        return 2

    rows = _read_jsonl(args.input)
    if not rows:
        print("no rows in input — nothing to calibrate", file=sys.stderr)
        return 2

    rater_kinds = {r.get("rater_kind", "silver") for r in rows}
    overall_kind = "gold" if rater_kinds == {"gold"} else "silver"

    if args.module == "EE":
        cal = _calibrate_ee(rows, args.rubric_version)
    else:
        cal = _calibrate_eo(rows, args.rubric_version)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cal.save(args.output)
    report_path = _write_report(cal, overall_kind, args.output)

    print(f"calibrator → {args.output}")
    print(f"report → {report_path}")
    for r in cal.reports:
        flag = "WARN" if r.kappa < 0.55 else "OK"
        print(f"  [{flag}] {r.dimension}: κ={r.kappa:.3f} r={r.pearson_r:.3f} MAE={r.mae:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
