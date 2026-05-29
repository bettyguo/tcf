"""Tests for `tcf_accel_content.quality.report_io`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tcf_accel_content.quality.report_io import (
    read_report,
    report_from_dict,
    report_to_dict,
    write_report,
)
from tcf_accel_content.types import QualityCheckResult, QualityReport


def _report(verdict: str = "pass") -> QualityReport:
    return QualityReport(
        item_id="some-item-id",
        checks=(
            QualityCheckResult(
                name="license_compatible", passed=True, severity="P0",
                detail="ok", metric=None,
            ),
            QualityCheckResult(
                name="length_balanced", passed=False, severity="P1",
                detail="too short", metric=0.45,
            ),
        ),
        verdict=verdict,  # type: ignore[arg-type]
        flags=("needs_human_review",),
    )


def test_to_dict_round_trips_via_from_dict() -> None:
    original = _report()
    blob = report_to_dict(original)
    recovered = report_from_dict(blob)
    assert recovered == original


def test_to_dict_includes_version_field() -> None:
    blob = report_to_dict(_report())
    assert blob["version"] == "1"


def test_to_dict_produces_json_serialisable_output() -> None:
    blob = report_to_dict(_report())
    # Round-trip via json so we know the output has no exotic objects.
    s = json.dumps(blob)
    assert json.loads(s) == blob


def test_from_dict_rejects_unknown_version() -> None:
    blob = report_to_dict(_report())
    blob["version"] = "99"
    with pytest.raises(ValueError, match="unsupported"):
        report_from_dict(blob)


def test_from_dict_rejects_invalid_verdict() -> None:
    blob = report_to_dict(_report())
    blob["verdict"] = "maybe"
    with pytest.raises(ValueError, match="invalid verdict"):
        report_from_dict(blob)


def test_from_dict_rejects_invalid_severity() -> None:
    blob = report_to_dict(_report())
    blob["checks"][0]["severity"] = "P9"
    with pytest.raises(ValueError, match="severity"):
        report_from_dict(blob)


def test_from_dict_rejects_missing_item_id() -> None:
    blob = report_to_dict(_report())
    del blob["item_id"]
    with pytest.raises(ValueError, match="item_id"):
        report_from_dict(blob)


def test_write_and_read_round_trip(tmp_path: Path) -> None:
    original = _report(verdict="p1_flag")
    path = tmp_path / "cache" / "quality" / "abc.json"
    write_report(original, path)
    assert path.exists()
    recovered = read_report(path)
    assert recovered == original


def test_write_is_atomic(tmp_path: Path) -> None:
    """A `<path>.tmp` should not linger after a successful write."""
    path = tmp_path / "r.json"
    write_report(_report(), path)
    assert not path.with_suffix(".json.tmp").exists()


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c" / "report.json"
    write_report(_report(), deep)
    assert deep.exists()


def test_write_overwrites_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_report(_report(verdict="pass"), path)
    write_report(_report(verdict="reject"), path)
    recovered = read_report(path)
    assert recovered.verdict == "reject"


def test_read_rejects_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="object"):
        read_report(path)
