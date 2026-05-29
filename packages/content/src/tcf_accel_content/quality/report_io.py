"""Serialise / deserialise `QualityReport` to JSON.

`phase3_design.md §5.7` calls for reports to be persisted to
``data/cache/quality/<item_id>.json`` for the audit trail. The format
is JSON-Lines-compatible (one report per line is also valid JSON) so
the audit can stream-process the corpus.

The codec is stdlib-only; no Pydantic round-trip needed because the
report types are frozen dataclasses with primitive-only fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from tcf_accel_content.types import QualityCheckResult, QualityReport

_VERSION: str = "1"


def report_to_dict(report: QualityReport) -> dict[str, object]:
    """Convert a `QualityReport` to a plain dict ready for json.dumps.

    The output carries a ``version`` field so the deserializer can
    detect schema drift; bumping ``_VERSION`` requires a follow-up
    that handles the older format.

    Example:
        >>> r = QualityReport(item_id="abc", checks=(), verdict="pass")
        >>> report_to_dict(r)["verdict"]
        'pass'
    """
    return {
        "version": _VERSION,
        "item_id": report.item_id,
        "verdict": report.verdict,
        "flags": list(report.flags),
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "severity": c.severity,
                "detail": c.detail,
                "metric": c.metric,
            }
            for c in report.checks
        ],
    }


def report_from_dict(blob: dict[str, object]) -> QualityReport:
    """Inverse of `report_to_dict`.

    Raises:
        ValueError: on a missing/unknown version, or a malformed
            check-result entry.
    """
    version = blob.get("version")
    if version != _VERSION:
        raise ValueError(
            f"unsupported QualityReport JSON version: {version!r} "
            f"(expected {_VERSION!r})",
        )
    checks_raw = blob.get("checks")
    if not isinstance(checks_raw, list):
        raise ValueError("QualityReport JSON: 'checks' must be a list")
    checks = tuple(_check_from_dict(c) for c in checks_raw)
    flags_raw = blob.get("flags") or []
    if not isinstance(flags_raw, list):
        raise ValueError("QualityReport JSON: 'flags' must be a list")
    verdict = blob.get("verdict")
    if verdict not in {"pass", "p1_flag", "reject"}:
        raise ValueError(f"QualityReport JSON: invalid verdict {verdict!r}")
    item_id = blob.get("item_id")
    if not isinstance(item_id, str):
        raise ValueError("QualityReport JSON: 'item_id' must be a string")
    return QualityReport(
        item_id=item_id,
        checks=checks,
        verdict=cast("str", verdict),  # type: ignore[arg-type]
        flags=tuple(str(f) for f in flags_raw),
    )


def write_report(report: QualityReport, path: Path) -> None:
    """Atomically write `report` as pretty JSON to `path`.

    Writes to ``<path>.tmp`` first and renames, so a killed process
    cannot leave a half-written file the audit would misread.

    Complexity: O(|report|).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(report_to_dict(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def read_report(path: Path) -> QualityReport:
    """Read and deserialise a `QualityReport` from disk."""
    blob = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(blob, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return report_from_dict(blob)


def _check_from_dict(blob: object) -> QualityCheckResult:
    """Parse one check-result entry."""
    if not isinstance(blob, dict):
        raise ValueError(f"check entry must be an object, got {type(blob).__name__}")
    name = blob.get("name")
    severity = blob.get("severity")
    passed = blob.get("passed")
    if not isinstance(name, str):
        raise ValueError("check 'name' must be a string")
    if severity not in {"P0", "P1", "info"}:
        raise ValueError(f"check 'severity' invalid: {severity!r}")
    if not isinstance(passed, bool):
        raise ValueError("check 'passed' must be a boolean")
    detail = blob.get("detail")
    if detail is not None and not isinstance(detail, str):
        raise ValueError("check 'detail' must be a string or null")
    metric = blob.get("metric")
    if metric is not None and not isinstance(metric, (int, float)):
        raise ValueError("check 'metric' must be a number or null")
    return QualityCheckResult(
        name=name,
        passed=passed,
        severity=cast("str", severity),  # type: ignore[arg-type]
        detail=detail,
        metric=float(metric) if metric is not None else None,
    )


__all__ = [
    "read_report",
    "report_from_dict",
    "report_to_dict",
    "write_report",
]
