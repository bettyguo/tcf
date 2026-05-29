"""Fixture item pool for the Phase 4 diagnostic.

The real content pool ships in Phase 5 (content pipeline + Postgres
`items` table). Phase 4 needs a *working* diagnostic so the API
contract for `/v1/diagnostic/*` can be honored end-to-end; the pool
below is a small, deterministic synthetic bank — eight items per skill,
spread across NCLC bands 3..11. Phase 5 replaces this entirely.

The seeds are sha256(skill + band + index) → first 16 hex → UUID, so
the same id appears across processes (the Phase 4 diagnostic is
deterministic given the same answer trace).
"""

from __future__ import annotations

import hashlib
from typing import Final
from uuid import UUID

from tcf_accel.schemas.scoring import SkillCode
from tcf_accel_sla.diagnostic import CandidateItem


def _seed_uuid(skill: SkillCode, band: int, idx: int) -> UUID:
    h = hashlib.sha256(f"diag::{skill}::{band}::{idx}".encode()).hexdigest()
    return UUID(h[:32])


def _build_pool() -> dict[SkillCode, list[CandidateItem]]:
    return {
        skill: [
            CandidateItem(
                item_id=_seed_uuid(skill, band, idx),
                difficulty=float(band),
                discrimination=1.0 + 0.1 * (idx - 0.5),
                band=band,
            )
            for band in range(3, 12)
            for idx in range(2)  # 2 items per band
        ]
        for skill in ("CO", "CE", "EE", "EO")
    }


DIAGNOSTIC_POOL: Final[dict[SkillCode, list[CandidateItem]]] = _build_pool()


def candidates_for(skill: SkillCode) -> list[CandidateItem]:
    """Return the (immutable-in-spirit) candidate list for the given skill."""
    return list(DIAGNOSTIC_POOL[skill])


__all__ = ["DIAGNOSTIC_POOL", "candidates_for"]
