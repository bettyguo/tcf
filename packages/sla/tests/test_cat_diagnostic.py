"""CAT diagnostic tests.

Invariants:
- Stops at variance ≤ threshold or item-cap.
- Doesn't re-pick already-administered items.
- Respects the same-difficulty-run cap.
- Posterior converges with the underlying true ability.
"""

from __future__ import annotations

import random
from uuid import UUID

from tcf_accel_sla.diagnostic.cat import (
    DIAGNOSTIC_MAX_ITEMS,
    SAME_DIFFICULTY_RUN_CAP,
    CandidateItem,
    DiagnosticSession,
    select_next_item,
)
from tcf_accel_sla.estimator import (
    bootstrap_posterior,
    irt_p_correct,
)


def _pool() -> list[CandidateItem]:
    """A diverse pool spanning NCLC 3..11."""
    return [
        CandidateItem(
            item_id=UUID(int=band * 100 + i),
            difficulty=float(band),
            discrimination=1.0,
            band=band,
        )
        for band in range(3, 12)
        for i in range(3)
    ]


def test_select_next_item_targets_posterior_mean() -> None:
    """Fisher info maximizes when difficulty = posterior mean."""
    p = bootstrap_posterior(self_report_nclc=7.0)
    pool = _pool()
    picked = select_next_item(p, pool, already_administered=[])
    assert picked is not None
    # Should pick a band-7 item (or close).
    assert picked.band == 7


def test_select_never_repeats_administered() -> None:
    p = bootstrap_posterior(self_report_nclc=7.0)
    pool = _pool()
    administered: list[CandidateItem] = [pool[3], pool[4]]  # arbitrary
    picked = select_next_item(p, pool, already_administered=administered)
    assert picked is not None
    assert picked.item_id not in {a.item_id for a in administered}


def test_same_difficulty_run_cap_enforced() -> None:
    """After SAME_DIFFICULTY_RUN_CAP items at the same band, the next must differ."""
    p = bootstrap_posterior(self_report_nclc=7.0)
    pool = _pool()
    # Hand-administered SAME_DIFFICULTY_RUN_CAP items at band 7.
    band_7 = [c for c in pool if c.band == 7]
    administered = band_7[:SAME_DIFFICULTY_RUN_CAP]
    picked = select_next_item(p, pool, already_administered=administered)
    assert picked is not None
    assert picked.band != 7


def test_session_stops_at_max_items() -> None:
    sess = DiagnosticSession.start(
        user_id=UUID(int=1), skill="CO", self_report_nclc=5.0,
    )
    pool = _pool()
    # Force-feed correct answers until we hit max-items.
    for _ in range(DIAGNOSTIC_MAX_ITEMS):
        item = sess.next_item(pool)
        if item is None:
            break
        sess.record_mcq(item, correct=True)
    assert sess.should_stop()
    assert len(sess.administered) <= DIAGNOSTIC_MAX_ITEMS


def test_session_stops_when_variance_threshold_met() -> None:
    sess = DiagnosticSession.start(
        user_id=UUID(int=1), skill="CO", self_report_nclc=5.0,
    )
    sess.stop_variance = 9.9  # immediate stop
    assert sess.should_stop()
    assert sess.next_item(_pool()) is None


def test_cat_converges_on_known_true_ability() -> None:
    """A learner with true NCLC=9 → posterior mean lands near 9 after CAT."""
    rng = random.Random(7)
    sess = DiagnosticSession.start(
        user_id=UUID(int=1), skill="CO", self_report_nclc=5.0,
    )
    sess.max_items = DIAGNOSTIC_MAX_ITEMS  # default 15
    pool = _pool()
    true_theta = 9.0
    while not sess.should_stop():
        item = sess.next_item(pool)
        if item is None:
            break
        prob = irt_p_correct(true_theta, item.difficulty, item.discrimination)
        correct = rng.random() < prob
        sess.record_mcq(item, correct=correct)
    # Within ±2 NCLC of true ability after ≤ 15 items (CAT noise tolerance).
    assert abs(sess.posterior.mean - true_theta) < 2.0
