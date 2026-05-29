"""Generate `tests/pedagogy/golden_learner.jsonl` — a deterministic synthetic learner trajectory.

Output: 200 `Interaction` records (the public projection of the
`interactions` table row) telling the story of a learner moving from
NCLC ≈ 5 to NCLC ≈ 7 over six weeks of practice. The trajectory is
hand-curated in *aggregate shape* (module mix, accuracy ramp, rating
distribution) and PRNG-filled in detail (item ids, rt_ms, exact
ratings) so the file is reproducible and reviewable.

Phase 2 ships the fixture + a parser test that asserts it deserializes
into the `Interaction` contract. Phase 4 ships the *behavioral* test:
the planner output on this trajectory is the golden output; any
deviation requires an intentional regeneration + diff review.

Usage:

    uv run python scripts/generate_golden_learner.py \\
        > tests/pedagogy/golden_learner.jsonl

The script is deterministic: seed 20260527 + the fixed structure below
produces byte-identical output across runs and platforms.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from tcf_accel.schemas.interaction import Interaction
from tcf_accel.schemas.item import Module

SEED = 20_260_527
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
START = datetime(2026, 4, 1, 9, 0, 0, tzinfo=UTC)

# ── Trajectory shape ─────────────────────────────────────────────
# 200 interactions across 6 weeks. The accuracy curve ramps from ~0.55
# to ~0.78 over the trajectory; rt_ms tightens from ~12s to ~7s.
N_INTERACTIONS = 200

# Weekly module mix (CO, CE, EE, EO) — sums to N_INTERACTIONS / 6 per week.
MODULE_MIX_BY_WEEK: list[dict[Module, int]] = [
    # Week 0: heavy CO + CE diagnostic
    {"CO": 12, "CE": 14, "EE": 4, "EO": 3},
    {"CO": 11, "CE": 12, "EE": 6, "EO": 4},
    # Week 2-3: rebalance toward weak skill (assume EE bottleneck)
    {"CO": 8,  "CE": 8,  "EE": 12, "EO": 5},
    {"CO": 8,  "CE": 8,  "EE": 12, "EO": 5},
    # Week 4-5: maintenance + mock-style mix
    {"CO": 9,  "CE": 10, "EE": 8,  "EO": 7},
    {"CO": 8,  "CE": 8,  "EE": 9,  "EO": 9},
]


def _accuracy_at(t_frac: float, module: Module) -> float:
    """Target accuracy ramp; module-dependent ceiling."""
    base = 0.55 + 0.25 * t_frac
    ceiling = {"CO": 0.85, "CE": 0.85, "EE": 0.75, "EO": 0.78}[module]
    return min(base, ceiling)


def _rt_at(t_frac: float, module: Module, rng: random.Random) -> int:
    """Target response time ramp; CO/CE faster than EE/EO."""
    mean = {"CO": 9000, "CE": 11000, "EE": 30000, "EO": 28000}[module]
    mean = int(mean * (1.3 - 0.5 * t_frac))
    return max(800, int(rng.gauss(mean, mean * 0.2)))


def _stable_uuid(rng: random.Random) -> UUID:
    """Deterministic UUID from the RNG (not a real UUIDv4)."""
    return UUID(int=rng.getrandbits(128))


def generate() -> list[Interaction]:
    """Build the trajectory."""
    rng = random.Random(SEED)
    out: list[Interaction] = []
    when = START
    session_id = _stable_uuid(rng)
    interactions_in_session = 0
    n_total = sum(sum(mix.values()) for mix in MODULE_MIX_BY_WEEK)
    if n_total != N_INTERACTIONS:
        msg = f"MODULE_MIX_BY_WEEK sums to {n_total}, expected {N_INTERACTIONS}"
        raise ValueError(msg)

    for week_idx, mix in enumerate(MODULE_MIX_BY_WEEK):
        for module, count in mix.items():
            for _ in range(count):
                # Start a new session every 12 items.
                if interactions_in_session >= 12:
                    session_id = _stable_uuid(rng)
                    interactions_in_session = 0

                t_frac = (week_idx * sum(MODULE_MIX_BY_WEEK[0].values()) + len(out)) / n_total
                target_acc = _accuracy_at(t_frac, module)

                # CO/CE: binary correctness. EE/EO: pending until graded later.
                if module in {"CO", "CE"}:
                    correct: bool | None = rng.random() < target_acc
                    rating = (
                        4 if correct and rng.random() < 0.45
                        else 3 if correct
                        else 2 if rng.random() < 0.6
                        else 1
                    )
                    graded_score: dict[str, object] | None = None
                else:
                    # Async-graded; the value would be filled in by Phase 7.
                    correct = None
                    rating = None
                    # ~half are already graded by the time the export runs.
                    if rng.random() < 0.55:
                        component = lambda: rng.randint(2, 4)  # noqa: E731
                        graded_score = {
                            "task_completion": component(),
                            "coherence_cohesion": component(),
                            "lexical_range": component(),
                            "grammatical_accuracy": component(),
                            "register_appropriateness": component(),
                            "total_20": int(round(target_acc * 20)),
                        }
                    else:
                        graded_score = None

                interaction = Interaction(
                    id=len(out) + 1,
                    user_id=USER_ID,
                    item_id=_stable_uuid(rng),
                    session_id=session_id,
                    module=module,
                    correct=correct,
                    raw_response={"answer": "o1"} if module in {"CO", "CE"} else {"length_words": rng.randint(80, 160)},
                    rt_ms=_rt_at(t_frac, module, rng),
                    rating=rating,
                    fsrs_stability=round(0.5 + t_frac * 4.0 + rng.gauss(0, 0.3), 3),
                    fsrs_difficulty=round(5.0 - t_frac * 1.5 + rng.gauss(0, 0.4), 3),
                    graded_score=graded_score,
                    created_at=when,
                )
                out.append(interaction)
                when += timedelta(seconds=int(rng.gauss(60, 25)) + interaction.rt_ms // 1000)
                interactions_in_session += 1
        # End of week: jump 1.5 days
        when += timedelta(days=1, hours=12)
    return out


def main(out_path: Path | None = None) -> None:
    """CLI entry point."""
    trajectory = generate()
    lines = [
        json.dumps(itx.model_dump(mode="json"), separators=(",", ":"), sort_keys=True)
        for itx in trajectory
    ]
    payload = "\n".join(lines) + "\n"
    if out_path is None:
        sys.stdout.write(payload)
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    main(arg)
