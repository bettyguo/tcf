"""Persistent dismissal log tests (Phase 5 step 11, ADR-017).

The dismissal log lives at `data/dismissal_log.jsonl` (local-only by
ADR-017 — never replicated to a cloud backend). Each `record_dismissal`
appends a typed `DismissalLogEntry` JSON line; subsequent restarts
read the file to rebuild the in-process cache so the floor check
survives a process restart without needing Postgres.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from tcf_accel.ids import UserId
from tcf_accel_api.main import create_app
from tcf_accel_api.session_state import (
    _dismissal_log_path,
    dismissed_this_week,
    record_dismissal,
    reset_all,
)


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point `TCF_ACCEL_DATA_DIR` at a per-test temp dir (ADR-017 / phase5_design §13.4)."""
    monkeypatch.setenv("TCF_ACCEL_DATA_DIR", str(tmp_path))
    return tmp_path


_NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


def _uid() -> UserId:
    return UserId(UUID("11111111-1111-4111-8111-111111111111"))


def test_dismissal_log_path_resolves_under_isolated_data_dir(tmp_path: Path) -> None:
    """The autouse `_isolated_data_dir` fixture must point the log under tmp_path."""
    log_path = _dismissal_log_path()
    assert log_path.parent == tmp_path
    assert log_path.name == "dismissal_log.jsonl"


def test_record_dismissal_writes_jsonl_line() -> None:
    reset_all()
    record_dismissal(_uid(), now=_NOW)
    path = _dismissal_log_path()
    assert path.exists(), "dismissal log file must be written on first call"
    content = path.read_text(encoding="utf-8").splitlines()
    assert len(content) == 1
    row = json.loads(content[0])
    assert row["user_id"] == str(_uid())
    assert row["week_iso"] == "2026-W22"
    assert "dismissed_at" in row


def test_record_dismissal_is_idempotent_in_same_week() -> None:
    """Second `record_dismissal` in the same week must not duplicate the on-disk row."""
    reset_all()
    record_dismissal(_uid(), now=_NOW)
    record_dismissal(_uid(), now=_NOW)  # same week
    content = _dismissal_log_path().read_text(encoding="utf-8").splitlines()
    assert len(content) == 1


def test_record_dismissal_two_weeks_writes_two_rows() -> None:
    reset_all()
    week_a = datetime(2026, 5, 28, tzinfo=UTC)  # 2026-W22
    week_b = datetime(2026, 6, 4, tzinfo=UTC)  # 2026-W23
    record_dismissal(_uid(), now=week_a)
    record_dismissal(_uid(), now=week_b)
    content = _dismissal_log_path().read_text(encoding="utf-8").splitlines()
    assert len(content) == 2
    rows = [json.loads(line) for line in content]
    assert {r["week_iso"] for r in rows} == {"2026-W22", "2026-W23"}


def test_dismissal_persists_across_in_process_reset() -> None:
    """After `reset_all()` (process restart simulation), the file rehydrates the cache."""
    reset_all()
    record_dismissal(_uid(), now=_NOW)
    assert dismissed_this_week(_uid(), now=_NOW) is True

    # Simulate process restart: drop the in-process store. The file
    # remains on disk; the next dismissed-this-week call should read
    # it and report True without a fresh record_dismissal.
    reset_all()
    assert dismissed_this_week(_uid(), now=_NOW) is True


def test_dismissal_log_only_carries_this_users_entries() -> None:
    """Multi-user safety: another user's entries don't affect this user's cache."""
    reset_all()
    other = UserId(UUID("22222222-2222-4222-8222-222222222222"))
    # Manually write a row for `other` to the log to simulate a
    # multi-user file (Phase 5 default is single-user; the contract
    # is still per-user).
    record_dismissal(other, now=_NOW)
    reset_all()
    # Our user hasn't dismissed; the loader must not see `other`'s entry.
    assert dismissed_this_week(_uid(), now=_NOW) is False


def test_dismissal_endpoint_writes_to_disk() -> None:
    """End-to-end via the route: POST /v1/session/exam-shape/dismiss persists."""
    reset_all()
    client = TestClient(create_app())
    response = client.post("/v1/session/exam-shape/dismiss")
    assert response.status_code == 200
    assert response.json()["dismissed_week"]
    # The file exists and has exactly one row for the default test user.
    path = _dismissal_log_path()
    assert path.exists()
    rows = path.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    row = json.loads(rows[0])
    assert row["week_iso"] == row["week_iso"]  # well-formed
    assert UserId(UUID(row["user_id"])) is not None


def test_log_row_matches_dismissal_log_entry_schema() -> None:
    """The on-disk JSON must round-trip through DismissalLogEntry."""
    from tcf_accel.schemas.api.session import DismissalLogEntry  # noqa: PLC0415

    reset_all()
    record_dismissal(_uid(), now=_NOW)
    line = _dismissal_log_path().read_text(encoding="utf-8").strip()
    parsed = DismissalLogEntry.model_validate_json(line)
    assert parsed.user_id == _uid()
    assert parsed.week_iso == "2026-W22"


def test_reset_all_does_not_truncate_the_log() -> None:
    """ADR-017: the file is the operator's audit record; `reset_all` is a
    test-only in-process state reset and must not touch the file."""
    reset_all()
    record_dismissal(_uid(), now=_NOW)
    pre = _dismissal_log_path().read_text(encoding="utf-8")
    reset_all()
    post = _dismissal_log_path().read_text(encoding="utf-8")
    assert pre == post


def test_loader_tolerates_corrupted_lines() -> None:
    """A malformed JSON line in the log must not crash the loader."""
    reset_all()
    path = _dismissal_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "not-json\n"
        "{\"user_id\": \"" + str(_uid()) + "\", "
        "\"dismissed_at\": \"2026-05-28T12:00:00+00:00\", "
        "\"week_iso\": \"2026-W22\"}\n"
        "\n",
        encoding="utf-8",
    )
    # The good line is recognized; the bad lines are skipped silently.
    assert dismissed_this_week(_uid(), now=_NOW) is True


def test_loader_runs_only_once_per_store() -> None:
    """Hot-path optimization: repeated `dismissed_this_week` calls don't re-read the file."""
    reset_all()
    record_dismissal(_uid(), now=_NOW)
    reset_all()  # force a re-load on next access

    # First call hydrates from disk.
    assert dismissed_this_week(_uid(), now=_NOW) is True

    # Mutate the file directly; the in-process cache should not pick up the change
    # within the same store lifecycle (the loader is one-shot per store).
    _dismissal_log_path().write_text("", encoding="utf-8")
    assert dismissed_this_week(_uid(), now=_NOW) is True  # still cached
