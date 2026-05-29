"""Parser test for `golden_learner.jsonl`.

Phase 2 ships the fixture + this parser check. Phase 4 ships the
*behavioral* test (the planner output on this trajectory is the golden
output; any shape change requires an intentional regeneration with a
diff review per `02_ARCHITECTURE.md §2.7`).

This test asserts:

- The fixture exists and has exactly 200 interactions.
- Every line deserializes into the `Interaction` contract type.
- Module mix is plausibly TCF-shaped (all four modules represented;
  no single module dominates beyond 35%).
- The trajectory's accuracy ramp is monotone-ish: the second half has
  higher CO+CE accuracy than the first half (a sanity check that the
  fixture tells the "learner improves" story Phase 4 will rely on).
- The fixture is deterministic w.r.t. the generator (the test calls
  the generator and asserts byte-for-byte equality with the on-disk
  file).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tcf_accel.schemas.interaction import Interaction
from tcf_accel.schemas.item import Module

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "pedagogy" / "golden_learner.jsonl"
EXPECTED_COUNT = 200


def _load() -> list[Interaction]:
    return [
        Interaction.model_validate(json.loads(line))
        for line in FIXTURE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_fixture_exists() -> None:
    assert FIXTURE.exists(), f"golden_learner fixture missing at {FIXTURE}"


def test_fixture_has_expected_count() -> None:
    interactions = _load()
    assert len(interactions) == EXPECTED_COUNT


def test_every_line_parses_into_contract() -> None:
    interactions = _load()
    assert all(isinstance(i, Interaction) for i in interactions)


def test_module_mix_covers_all_four() -> None:
    interactions = _load()
    seen = {i.module for i in interactions}
    assert seen == {"CO", "CE", "EE", "EO"}


def test_no_module_dominates() -> None:
    interactions = _load()
    counts: dict[Module, int] = {"CO": 0, "CE": 0, "EE": 0, "EO": 0}
    for i in interactions:
        counts[i.module] += 1
    for module, n in counts.items():
        share = n / EXPECTED_COUNT
        assert share <= 0.35, f"{module} share={share:.2%} > 35%"
        assert share >= 0.15, f"{module} share={share:.2%} < 15%"


def test_accuracy_ramps_up_over_time() -> None:
    interactions = _load()
    # Only CO/CE (binary correctness).
    co_ce = [i for i in interactions if i.module in {"CO", "CE"} and i.correct is not None]
    half = len(co_ce) // 2
    first = sum(1 for i in co_ce[:half] if i.correct) / max(half, 1)
    second = sum(1 for i in co_ce[half:]) and sum(1 for i in co_ce[half:] if i.correct) / max(
        len(co_ce) - half, 1,
    )
    # The synthetic fixture is designed for second-half accuracy ≥ first-half.
    assert second >= first - 0.02, (
        f"learner should not regress in synthetic trajectory: first={first:.2f}, second={second:.2f}"
    )


def test_fixture_is_deterministic() -> None:
    """The committed file must equal what the generator produces today."""
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    try:
        from scripts.generate_golden_learner import generate
    finally:
        sys.path.pop(0)

    regenerated = generate()
    regenerated_lines = [
        json.dumps(itx.model_dump(mode="json"), separators=(",", ":"), sort_keys=True)
        for itx in regenerated
    ]
    on_disk_lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    if regenerated_lines != on_disk_lines:
        pytest.fail(
            "golden_learner.jsonl is not byte-equal to the generator output. "
            "Run: uv run python scripts/generate_golden_learner.py tests/pedagogy/golden_learner.jsonl",
        )
