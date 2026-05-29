"""Twelve archetypal learner cohorts for Phase 4 audit.

Each cohort is a `Cohort` tuple: (id, label, true_per_skill_nclc, target_nclc).
These archetypes span the realistic TCF-Canada applicant population:

1.  Generic B1 across the board, targeting B2 (NCLC 7).
2.  Strong CO/CE, weak EE/EO — heritage speaker.
3.  Strong production, weak reception — community speaker, low literacy.
4.  Balanced A2 targeting B1 — beginner with realistic target.
5.  Balanced B2 targeting C1 — advanced learner, high ceiling.
6.  Bottleneck EE only — analytical writer's nightmare.
7.  Bottleneck EO only — speaking-anxious learner.
8.  Reception weakness only — print-only learner.
9.  Balanced near-C1 targeting C2 — exam-bound polyglot.
10. Newcomer A1 across the board, targeting B1 in 12 weeks (ambitious).
11. Production-strong/reception-weak diaspora speaker.
12. Hypothetical "already at target" — minimum-allocation regression test.

The audit checks (see `tests/pedagogy/test_synthetic_cohorts.py`):
- Time allocation respects the production-skill floor when the
  bottleneck is EE or EO.
- The planner doesn't promise the impossible (no plan claims +7 NCLC
  in 12 weeks).
- The readiness traffic light correctly refuses to predict on fresh
  posteriors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from tcf_accel.schemas.scoring import SkillCode
from tcf_accel_sla.estimator import SkillPosterior


@dataclass(frozen=True)
class Cohort:
    """One archetypal learner."""

    id: int
    label: str
    true_nclc: dict[SkillCode, float]
    target_nclc: int

    def confident_posteriors(self) -> dict[SkillCode, SkillPosterior]:
        """A confident posterior centered on the cohort's true NCLC per skill.

        Used by the allocator + readiness tests; the cohort fixture
        bakes in `n_obs=40`, `variance=0.2`, and 4 distinct bands so
        every skill clears the ADR-025 confidence gate by construction.
        """
        return {
            skill: SkillPosterior(
                skill=skill,
                mean=nclc,
                variance=0.2,
                n_obs=40,
                difficulty_bands_seen=frozenset({3, 5, 7, 9}),
            )
            for skill, nclc in self.true_nclc.items()
        }


COHORTS: Final[tuple[Cohort, ...]] = (
    Cohort(
        id=1,
        label="generic_b1_targeting_b2",
        true_nclc={"CO": 5.0, "CE": 5.0, "EE": 5.0, "EO": 5.0},
        target_nclc=7,
    ),
    Cohort(
        id=2,
        label="heritage_strong_reception_weak_production",
        true_nclc={"CO": 8.0, "CE": 8.0, "EE": 4.0, "EO": 4.0},
        target_nclc=7,
    ),
    Cohort(
        id=3,
        label="community_strong_production_low_literacy",
        true_nclc={"CO": 7.0, "CE": 3.0, "EE": 3.0, "EO": 6.0},
        target_nclc=7,
    ),
    Cohort(
        id=4,
        label="beginner_a2_targeting_b1",
        true_nclc={"CO": 3.0, "CE": 3.0, "EE": 3.0, "EO": 3.0},
        target_nclc=5,
    ),
    Cohort(
        id=5,
        label="advanced_b2_targeting_c1",
        true_nclc={"CO": 7.0, "CE": 7.0, "EE": 7.0, "EO": 7.0},
        target_nclc=9,
    ),
    Cohort(
        id=6,
        label="ee_bottleneck_only",
        true_nclc={"CO": 7.0, "CE": 7.0, "EE": 4.0, "EO": 7.0},
        target_nclc=8,
    ),
    Cohort(
        id=7,
        label="eo_bottleneck_only",
        true_nclc={"CO": 7.0, "CE": 7.0, "EE": 7.0, "EO": 4.0},
        target_nclc=8,
    ),
    Cohort(
        id=8,
        label="reception_weakness_only",
        true_nclc={"CO": 4.0, "CE": 4.0, "EE": 7.0, "EO": 7.0},
        target_nclc=7,
    ),
    Cohort(
        id=9,
        label="near_c1_targeting_c2",
        true_nclc={"CO": 9.0, "CE": 9.0, "EE": 9.0, "EO": 9.0},
        target_nclc=11,
    ),
    Cohort(
        id=10,
        label="newcomer_ambitious_a1_to_b1",
        true_nclc={"CO": 2.0, "CE": 2.0, "EE": 2.0, "EO": 2.0},
        target_nclc=5,
    ),
    Cohort(
        id=11,
        label="diaspora_production_strong",
        true_nclc={"CO": 4.0, "CE": 4.0, "EE": 8.0, "EO": 8.0},
        target_nclc=7,
    ),
    Cohort(
        id=12,
        label="already_at_target",
        true_nclc={"CO": 9.0, "CE": 9.0, "EE": 9.0, "EO": 9.0},
        target_nclc=9,
    ),
)
assert len(COHORTS) == 12


__all__ = ["COHORTS", "Cohort"]
