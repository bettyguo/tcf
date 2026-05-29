"""Computer-adaptive testing (CAT) for the diagnostic.

Master prompt §6.2 names "diagnostic in ≤ 60 min, refuses to over-predict."
The CAT routine in `04_LEARNER_MODEL.md §1.3`:

1. Start at the learner's self-reported difficulty (default B1 = NCLC 5).
2. Update the posterior after each item.
3. Select the next item to maximize Fisher information at the posterior
   mean, with a same-difficulty-run cap (≤ 3) to avoid frustration.
4. Stop on posterior variance ≤ 0.3, or 15 items, or 10 minutes elapsed
   (the elapsed-time gate is enforced by the API layer).

This module is purely in-memory and serialization-free — the API layer
(routes/diagnostic.py) owns the persistence story.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final
from uuid import UUID

from tcf_accel.schemas.scoring import SkillCode

from tcf_accel_sla.estimator.nclc import (
    SkillPosterior,
    bootstrap_posterior,
    fisher_information,
    update_with_mcq,
    update_with_rubric,
)

DIAGNOSTIC_MAX_ITEMS: Final[int] = 15
DIAGNOSTIC_STOP_VARIANCE: Final[float] = 0.3
SAME_DIFFICULTY_RUN_CAP: Final[int] = 3


@dataclass(frozen=True)
class CandidateItem:
    """A pool item presented to `select_next_item`.

    The CAT cares only about the IRT parameters and the rough NCLC
    difficulty (used by the same-difficulty-run cap). The full `Item`
    payload is irrelevant at selection time — the API layer hydrates
    it once the id is chosen.
    """

    item_id: UUID
    difficulty: float       # 2PL `b`, in NCLC units
    discrimination: float   # 2PL `a`
    band: int               # CEFR band as NCLC integer (used by run cap)


def select_next_item(
    posterior: SkillPosterior,
    candidates: list[CandidateItem],
    already_administered: list[CandidateItem],
) -> CandidateItem | None:
    """Pick the next CAT item by max Fisher information at posterior mean.

    Tie-broken deterministically by item_id so audits get reproducible
    paths. Returns None if the candidate pool is exhausted (no items
    left after filtering for already-administered + run-cap).

    Same-difficulty run cap: if the last `SAME_DIFFICULTY_RUN_CAP` items
    share a band, exclude further items at that band — the spec says
    "to avoid frustration."
    """
    administered_ids = {c.item_id for c in already_administered}
    pool = [c for c in candidates if c.item_id not in administered_ids]
    if not pool:
        return None

    # Same-difficulty-run cap.
    if len(already_administered) >= SAME_DIFFICULTY_RUN_CAP:
        recent = already_administered[-SAME_DIFFICULTY_RUN_CAP:]
        recent_bands = {c.band for c in recent}
        if len(recent_bands) == 1:
            (banned_band,) = recent_bands
            filtered = [c for c in pool if c.band != banned_band]
            if filtered:  # only enforce if there's still something to pick
                pool = filtered

    # Pick max-information; tie-break by item_id (stable, deterministic).
    def score(c: CandidateItem) -> tuple[float, str]:
        info = fisher_information(posterior.mean, c.difficulty, c.discrimination)
        return (-info, str(c.item_id))

    return min(pool, key=score)


@dataclass
class DiagnosticSession:
    """One in-flight CAT session for one skill.

    The session is mutable by design: the API layer holds it in memory
    between requests (for v1, an in-process dict; later, a Redis-backed
    store keyed by session id).
    """

    user_id: UUID
    skill: SkillCode
    posterior: SkillPosterior
    administered: list[CandidateItem] = field(default_factory=list)
    max_items: int = DIAGNOSTIC_MAX_ITEMS
    stop_variance: float = DIAGNOSTIC_STOP_VARIANCE

    @classmethod
    def start(
        cls,
        *,
        user_id: UUID,
        skill: SkillCode,
        self_report_nclc: float = 5.0,
    ) -> DiagnosticSession:
        """Initialize a session with a prior centered on the self-report."""
        return cls(
            user_id=user_id,
            skill=skill,
            posterior=bootstrap_posterior(
                skill=skill, self_report_nclc=self_report_nclc,
            ),
        )

    def should_stop(self) -> bool:
        """The CAT stopping rule: variance ≤ threshold OR item-cap hit."""
        return (
            self.posterior.variance <= self.stop_variance
            or len(self.administered) >= self.max_items
        )

    def next_item(self, candidates: list[CandidateItem]) -> CandidateItem | None:
        """Return the next item to present, or None if we should stop."""
        if self.should_stop():
            return None
        return select_next_item(self.posterior, candidates, self.administered)

    def record_mcq(
        self,
        item: CandidateItem,
        *,
        correct: bool,
    ) -> SkillPosterior:
        """Fold an MCQ outcome into the posterior; append to administered."""
        self.posterior = update_with_mcq(
            self.posterior,
            item_difficulty=item.difficulty,
            discrimination=item.discrimination,
            correct=correct,
        )
        self.administered.append(item)
        return self.posterior

    def record_rubric(
        self,
        item: CandidateItem,
        *,
        rubric_total_20: float,
        obs_noise_sigma: float = 1.0,
    ) -> SkillPosterior:
        """Fold a rubric-scored EE/EO outcome into the posterior."""
        self.posterior = update_with_rubric(
            self.posterior,
            rubric_total_20=rubric_total_20,
            prompt_target_nclc=item.difficulty,
            obs_noise_sigma=obs_noise_sigma,
        )
        self.administered.append(item)
        return self.posterior


__all__ = [
    "DIAGNOSTIC_MAX_ITEMS",
    "DIAGNOSTIC_STOP_VARIANCE",
    "SAME_DIFFICULTY_RUN_CAP",
    "CandidateItem",
    "DiagnosticSession",
    "select_next_item",
]
