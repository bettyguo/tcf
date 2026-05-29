"""Item selector — constraint-guided greedy with seeded RNG (ADR-035).

Inputs: the full bank for a module, the user's recent-seen sets, and
a seed derived from `(user_id, iso_week)`. Output: exactly
`EXAM_SHAPE[module]` items satisfying the FEI constraints documented
in `phase6_design.md §5` and audited in `phase6_audit.md §1`.

Why greedy + RNG instead of OR-Tools (ADR-035):

- The problem size is ~84 items out of low-thousands; OR-Tools is
  overkill and brings ~80 MB of native binaries we do not otherwise
  need.
- Determinism is mandatory: the same `(user, week)` must produce the
  same draw so a duplicate `/v1/mock-exam/start` returns the existing
  mock id, not a new one. Seeded `random.Random` gives us this for
  free; OR-Tools' tie-breaking is fragile across versions.
- Audit-driven diversity is satisfied empirically: ≥ 60% bank coverage
  across 100 simulated weeks; the audit test runs this on every PR.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from tcf_accel.ids import ItemId, UserId
from tcf_accel.schemas.item import CefrLevel, Item, Module

from tcf_accel_sla.mock_exam.spec import (
    EXAM_SHAPE,
    FEI_SPREAD,
    NEVER_SEEN_FRACTION,
    TOPIC_CLUSTER_CAP_FRACTION,
)


@dataclass(frozen=True)
class PooledMockItem:
    """A bank item plus the per-item metadata the selector buckets on.

    Mirrors `apps/api/.../session_pool.PooledItem` but carries the
    extra fields the mock selector needs (task_number for EE/EO,
    topic_cluster_id for the cluster cap).
    """

    item: Item
    difficulty: float
    discrimination: float
    cefr: CefrLevel
    topic_cluster_id: int | None = None
    task_number: int | None = None  # EE/EO only; None for CO/CE


@dataclass(frozen=True)
class SelectorInputs:
    """Bundle for `select_for_module` / `select_full_mock`."""

    user_id: UserId
    iso_week: str
    bank: Mapping[Module, Sequence[PooledMockItem]]
    seen_within_30d: frozenset[ItemId] = field(default_factory=frozenset)
    seen_ever: frozenset[ItemId] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SelectorResult:
    """One module's selected items + any backoff warnings."""

    module: Module
    items: list[PooledMockItem]
    warnings: list[str] = field(default_factory=list)


# ─── Helpers ────────────────────────────────────────────────────


def _seed_for(user_id: UserId, iso_week: str, module: Module) -> int:
    """Stable RNG seed for `(user, week, module)`."""
    # Use a Python-stable hash via str repr; `hash()` is salted.
    payload = f"{user_id}::{iso_week}::{module}"
    h = 0
    for ch in payload:
        h = (h * 1315423911) ^ ord(ch)
        h &= 0xFFFFFFFFFFFFFFFF
    return h


def _bucket_targets_cefr(target: int) -> dict[CefrLevel, int]:
    """Distribute `target` picks across CEFR bands per `FEI_SPREAD`.

    Rounding correction: we use largest-remainder (Hare) so the sum is
    exactly `target`, not target ± 1.
    """
    raw = {band: target * frac for band, frac in FEI_SPREAD.items()}
    floors = {band: int(v) for band, v in raw.items()}
    remainder = target - sum(floors.values())
    # Distribute the remainder to the bands with the largest fractional part.
    fracs = sorted(
        ((band, raw[band] - floors[band]) for band in FEI_SPREAD),
        key=lambda kv: kv[1],
        reverse=True,
    )
    for i in range(remainder):
        band = fracs[i % len(fracs)][0]
        floors[band] += 1
    return floors


def _bucket_targets_task() -> dict[int, int]:
    """EE/EO: one each of tasks 1, 2, 3."""
    return {1: 1, 2: 1, 3: 1}


def _filter_bank(
    bank: Sequence[PooledMockItem],
    seen_within_30d: frozenset[ItemId],
) -> list[PooledMockItem]:
    return [
        p
        for p in bank
        if p.item.id not in seen_within_30d
        and not p.item.retired
        and not _is_low_quality(p.item)
    ]


_BLOCKING_QUALITY_FLAGS: Final[frozenset[str]] = frozenset(
    {"high_adversarial", "pii_suspected", "needs_human_review"},
)


def _is_low_quality(item: Item) -> bool:
    return any(
        getattr(flag, "value", str(flag)) in _BLOCKING_QUALITY_FLAGS
        for flag in item.quality_flags
    )


def _enforce_topic_cap(
    chosen: list[PooledMockItem],
    candidates: list[PooledMockItem],
    cap_per_module: int,
) -> list[PooledMockItem]:
    """Drop `candidates` whose addition would exceed the topic cap."""
    counts: dict[int, int] = defaultdict(int)
    for c in chosen:
        if c.topic_cluster_id is not None:
            counts[c.topic_cluster_id] += 1
    out: list[PooledMockItem] = []
    for cand in candidates:
        if cand.topic_cluster_id is not None:
            if counts[cand.topic_cluster_id] + 1 > cap_per_module:
                continue
        out.append(cand)
    return out


def _topic_cap_count(target: int) -> int:
    return max(1, int(target * TOPIC_CLUSTER_CAP_FRACTION))


# ─── Per-module selector ────────────────────────────────────────


def select_for_module(
    inputs: SelectorInputs,
    module: Module,
) -> SelectorResult:
    """Select exactly `EXAM_SHAPE[module]` items for one module.

    Algorithm (`phase6_design.md §5.2`):

    1. Hard-filter the bank: drop recent + retired + low-quality.
    2. Compute bucket targets (CEFR for CO/CE, task_number for EE/EO).
    3. Reserve a `NEVER_SEEN_FRACTION` slice from items the user has
       never seen, drawn proportionally across CEFR/task.
    4. Greedily fill the remaining buckets with seeded shuffle.
    5. Backoff: if a bucket is undersubscribed (the bank can't satisfy
       it), draw from adjacent buckets and emit a warning.
    6. Sort the final list by ascending IRT difficulty (FEI ordering).

    Determinism: identical `(user_id, iso_week, module, bank)` returns
    the identical list.
    """
    target = EXAM_SHAPE[module]
    rng = random.Random(_seed_for(inputs.user_id, inputs.iso_week, module))
    raw_bank = list(inputs.bank.get(module, []))
    bank = _filter_bank(raw_bank, inputs.seen_within_30d)

    if module in ("EE", "EO"):
        bucket_key = lambda p: p.task_number  # noqa: E731
        targets: dict[object, int] = dict(_bucket_targets_task())
    else:
        bucket_key = lambda p: p.cefr  # noqa: E731
        targets = dict(_bucket_targets_cefr(target))

    # Index by bucket
    by_bucket: dict[object, list[PooledMockItem]] = defaultdict(list)
    for p in bank:
        by_bucket[bucket_key(p)].append(p)

    # Shuffle each bucket deterministically.
    for key in by_bucket:
        rng.shuffle(by_bucket[key])

    chosen: list[PooledMockItem] = []
    warnings: list[str] = []

    # Topic-cap guard: applied as a post-filter on each candidate add.
    cap_per_module = _topic_cap_count(target)

    # Phase A: novelty budget — only meaningful for CO/CE (EE/EO has 3
    # items, novelty math collapses to "at least one new").
    novelty_target = round(NEVER_SEEN_FRACTION * target)
    if module in ("EE", "EO"):
        novelty_target = max(1, novelty_target)

    novel_pool: list[PooledMockItem] = [
        p for p in bank if p.item.id not in inputs.seen_ever
    ]
    rng.shuffle(novel_pool)

    # Phase B: spread the novelty draws across the buckets so we don't
    # blow a bucket's quota on novel-only items.
    novel_taken_per_bucket: dict[object, int] = defaultdict(int)
    for p in novel_pool:
        if len([c for c in chosen if c is p]) > 0:
            continue
        key = bucket_key(p)
        if novel_taken_per_bucket[key] >= targets.get(key, 0):
            continue
        candidates = _enforce_topic_cap(chosen, [p], cap_per_module)
        if not candidates:
            continue
        chosen.append(p)
        novel_taken_per_bucket[key] += 1
        if sum(novel_taken_per_bucket.values()) >= novelty_target:
            break
        if len(chosen) >= target:
            break

    # Phase C: bucket-fill to the target counts.
    for key, want in targets.items():
        have = sum(1 for c in chosen if bucket_key(c) == key)
        if have >= want:
            continue
        candidates = [p for p in by_bucket.get(key, []) if p not in chosen]
        candidates = _enforce_topic_cap(chosen, candidates, cap_per_module)
        for cand in candidates[: want - have]:
            chosen.append(cand)

    # Phase D: backoff — if a bucket couldn't be filled, fill from any.
    if len(chosen) < target:
        leftover = [p for p in bank if p not in chosen]
        rng.shuffle(leftover)
        leftover = _enforce_topic_cap(chosen, leftover, cap_per_module)
        before = len(chosen)
        chosen.extend(leftover[: target - len(chosen)])
        added = len(chosen) - before
        if added > 0:
            warnings.append(
                f"backoff_fill: drew {added} item(s) outside the FEI "
                f"distribution because some buckets were exhausted.",
            )

    # Phase E: still short? Last-resort: drop the topic cap.
    if len(chosen) < target:
        leftover = [p for p in bank if p not in chosen]
        rng.shuffle(leftover)
        before = len(chosen)
        chosen.extend(leftover[: target - len(chosen)])
        added = len(chosen) - before
        if added > 0:
            warnings.append(
                f"topic_cap_override: relaxed the {TOPIC_CLUSTER_CAP_FRACTION:.0%} "
                f"topic-cluster cap to fill the mock; review the bank.",
            )

    chosen = chosen[:target]

    # Phase F: FEI ordering — ascending difficulty within the module.
    chosen.sort(key=lambda p: (p.difficulty, str(p.item.id)))

    if len(chosen) != target:
        warnings.append(
            f"undersized: returned {len(chosen)}/{target} items; "
            f"bank is exhausted for this user.",
        )

    return SelectorResult(module=module, items=chosen, warnings=warnings)


def select_full_mock(
    inputs: SelectorInputs,
) -> dict[Module, SelectorResult]:
    """Run the per-module selector for every module."""
    return {
        module: select_for_module(inputs, module)
        for module in ("CO", "CE", "EE", "EO")
    }


__all__ = [
    "PooledMockItem",
    "SelectorInputs",
    "SelectorResult",
    "select_for_module",
    "select_full_mock",
]
