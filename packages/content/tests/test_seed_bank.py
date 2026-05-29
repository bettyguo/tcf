"""Tests for `tcf_accel_content.seed_bank`."""

from __future__ import annotations

from pathlib import Path

import pytest
from tcf_accel_content.load import InMemoryBankWriter
from tcf_accel_content.seed_bank import (
    BankStats,
    ModuleStats,
    main,
    main_capture,
    render,
    run_build,
)

# ─── run_build ─────────────────────────────────────────────────


def test_run_build_default_targets_persist_all_items() -> None:
    stats, writer = run_build()
    # Default targets: CE=8, CO=4, EE=4, EO=4 → 20 items.
    assert writer.count() == 20
    for module in ("CE", "CO", "EE", "EO"):
        m = stats.per_module[module]
        assert m.persisted == m.target
        assert m.rejected == 0
        assert m.already_present == 0


def test_run_build_with_zero_targets_persists_nothing() -> None:
    _, writer = run_build(target_ce=0, target_co=0, target_ee=0, target_eo=0)
    assert writer.count() == 0


def test_run_build_clamps_to_seed_pool_size() -> None:
    """CE seed pool currently has 8 entries; over-asking is a soft cap."""
    stats, writer = run_build(
        target_ce=1000, target_co=0, target_ee=0, target_eo=0,
    )
    # CE pool length is the actual ceiling — see _CE_PASSAGES.
    assert stats.per_module["CE"].persisted <= 8
    # And every persisted item came from the foundation seed source.
    for item in writer.all_items():
        assert item.provenance.source == "foundation_ce_seed"


def test_run_build_is_idempotent_on_same_seed_and_writer() -> None:
    _, writer = run_build()
    stats2, _ = run_build(writer=writer)
    assert writer.count() == 20  # no growth on second build
    assert stats2.total_persisted() == 0
    # Everything reported as already_present.
    for m in stats2.per_module.values():
        assert m.already_present == m.target


def test_run_build_rejects_unsupported_mode() -> None:
    with pytest.raises(ValueError, match="open-only"):
        run_build(mode="with-operator-ingest")  # type: ignore[arg-type]


def test_run_build_covers_all_four_modules() -> None:
    _, writer = run_build()
    modules = {item.module for item in writer.all_items()}
    assert modules == {"CO", "CE", "EE", "EO"}


def test_run_build_ee_task_distribution_covers_t1_t2_t3() -> None:
    """The round-robin EE plan touches every task with target ≥ 4."""
    _, writer = run_build(target_ce=0, target_co=0, target_ee=4, target_eo=0)
    ee_items = [i for i in writer.all_items() if i.module == "EE"]
    task_numbers = {
        i.content.task_number  # type: ignore[union-attr]
        for i in ee_items
    }
    assert task_numbers == {1, 2, 3}


def test_run_build_eo_task_distribution_covers_t1_t2_t3() -> None:
    _, writer = run_build(target_ce=0, target_co=0, target_ee=0, target_eo=3)
    eo_items = [i for i in writer.all_items() if i.module == "EO"]
    task_numbers = {
        i.content.task_number  # type: ignore[union-attr]
        for i in eo_items
    }
    assert task_numbers == {1, 2, 3}


def test_run_build_records_cefr_distribution() -> None:
    stats, writer = run_build()
    # The total across the level counter equals the bank size.
    assert sum(stats.cefr_levels.values()) == writer.count()


def test_run_build_co_seeds_attach_acoustic_via_provenance_only() -> None:
    """Foundation CO seeds do not populate acoustic features (the
    `_CO_SEEDS` list omits them); the bank items therefore have
    co_acoustic=None. Phase 3 follow-up will populate these from MFA."""
    _, writer = run_build(target_ce=0, target_co=4, target_ee=0, target_eo=0)
    co_items = [i for i in writer.all_items() if i.module == "CO"]
    for item in co_items:
        assert item.metadata.co_acoustic is None


# ─── render ────────────────────────────────────────────────────


def test_render_includes_summary_header() -> None:
    stats, writer = run_build()
    text = render(stats, writer)
    assert "Foundation Bank Build Summary" in text
    assert "**Mode**: open-only" in text


def test_render_includes_per_module_table() -> None:
    stats, writer = run_build()
    text = render(stats, writer)
    assert "| Module | Target | Persisted" in text
    for module in ("CO", "CE", "EE", "EO"):
        assert f"| {module} |" in text


def test_render_includes_cefr_distribution_table() -> None:
    stats, writer = run_build()
    text = render(stats, writer)
    assert "## CEFR-level distribution" in text
    for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
        assert f"| {level} |" in text


def test_render_lists_sample_item_ids_per_module() -> None:
    stats, writer = run_build()
    text = render(stats, writer)
    assert "Per-module sample item ids" in text


def test_render_handles_zero_items() -> None:
    """No persisted items should not divide-by-zero in CEFR shares."""
    stats = BankStats(mode="open-only", seed=0)
    text = render(stats, InMemoryBankWriter())
    assert "Foundation Bank Build Summary" in text
    assert "0.0%" in text


def test_module_stats_defaults_are_zero() -> None:
    m = ModuleStats()
    assert m.target == m.persisted == m.rejected == 0


# ─── main / main_capture ───────────────────────────────────────


def test_main_capture_runs_with_default_args() -> None:
    code, text = main_capture([])
    assert code == 0
    assert "Foundation Bank Build Summary" in text


def test_main_capture_honours_custom_targets() -> None:
    code, text = main_capture([
        "--target-ce", "2", "--target-co", "1",
        "--target-ee", "0", "--target-eo", "0",
    ])
    assert code == 0
    assert "| CE | 2 |" in text
    assert "| CO | 1 |" in text


def test_main_writes_to_out_file_when_provided(tmp_path: Path) -> None:
    out_path = tmp_path / "stats.md"
    code = main([
        "--target-ce", "1", "--target-co", "1",
        "--target-ee", "1", "--target-eo", "1",
        "--out", str(out_path),
    ])
    assert code == 0
    text = out_path.read_text(encoding="utf-8")
    assert "Foundation Bank Build Summary" in text


def test_main_returns_2_on_unsupported_mode(capsys: pytest.CaptureFixture[str]) -> None:
    # argparse rejects unknown choices before our code runs.
    with pytest.raises(SystemExit) as exc:
        main(["--mode", "with-operator-ingest"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err.lower()


def test_main_capture_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "seed_bank" in captured.out.lower()
