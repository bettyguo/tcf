"""EO examiner follow-up stub (`phase5_design.md §12.2`).

For Task 1 (Q&A) and Task 3 (defense) the examiner asks a follow-up
based on the candidate's response. In production the follow-up is
LLM-generated via the LiteLLM gateway (operator opt-in); in default
local mode this module's deterministic pool stands in.

The audit (`phase5_audit.md §14`) gates the local stub at ≥ 8 distinct
follow-ups per task. The pool below ships 12 per task to leave
headroom; the seed determines the rotation so identical transcripts
get identical follow-ups (idempotent under retries).
"""

from __future__ import annotations

import hashlib
from typing import Final

# Per-task pool. Each list is the candidate follow-up phrases; the
# selector picks `n` indices deterministically via `seed_text`. The
# audit gates `len(unique) >= 8` per task.
_FOLLOW_UP_POOL: Final[dict[int, tuple[str, ...]]] = {
    1: (
        "Pouvez-vous m'en dire un peu plus à ce sujet ?",
        "Et pourquoi est-ce important pour vous ?",
        "Avez-vous un exemple récent ?",
        "Qu'est-ce qui vous a amené à penser cela ?",
        "Comment réagissent vos proches à cela ?",
        "Y a-t-il un aspect que vous trouvez plus difficile ?",
        "Si vous aviez le choix, que feriez-vous différemment ?",
        "Comment cela se passe-t-il typiquement en semaine ?",
        "Quels conseils donneriez-vous à un débutant ?",
        "Comment cela a-t-il évolué ces dernières années ?",
        "Y a-t-il un souvenir particulier qui vous revient ?",
        "Que diriez-vous à quelqu'un qui hésite ?",
    ),
    3: (
        "Mais ne pourrait-on pas argumenter le contraire ?",
        "Quelles seraient les conséquences à long terme ?",
        "Comment répondriez-vous à ceux qui s'y opposent ?",
        "N'est-ce pas un peu simpliste comme position ?",
        "Avez-vous des données qui soutiennent ce point de vue ?",
        "Cette solution est-elle vraiment applicable partout ?",
        "Quelles alternatives avez-vous envisagées ?",
        "Que pensez-vous des coûts pour la société ?",
        "Cela ne risque-t-il pas de désavantager certains groupes ?",
        "Pouvez-vous nuancer votre position ?",
        "Et si les circonstances changeaient radicalement ?",
        "Comment concilier cela avec les contraintes pratiques ?",
    ),
    # Task 2 doesn't have follow-ups in the FEI shape (it's a single-
    # response describe/compare); kept absent here so a Task 2 caller
    # gets an empty list rather than a wrong-task follow-up.
}


def sample_follow_ups(*, task_number: int, seed_text: str, n: int = 2) -> list[str]:
    """Deterministically pick `n` follow-ups for the given task + seed.

    Returns an empty list for tasks without a follow-up pool (Task 2).
    Picks without repetition; if the pool is smaller than `n` the full
    pool is returned.

    Example:
        >>> picks = sample_follow_ups(task_number=1, seed_text="x", n=2)
        >>> len(picks)
        2
        >>> sample_follow_ups(task_number=2, seed_text="x")
        []

    Complexity: O(n) — small constant `n`.
    """
    pool = _FOLLOW_UP_POOL.get(task_number, ())
    if not pool:
        return []
    n = min(n, len(pool))
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    # Walk the pool starting at a seed-derived offset, stepping by an
    # odd stride so consecutive picks don't repeat.
    start = digest[0] % len(pool)
    stride = (digest[1] | 1) % len(pool) or 1  # ensure non-zero
    seen: set[int] = set()
    picks: list[str] = []
    idx = start
    while len(picks) < n and len(seen) < len(pool):
        if idx not in seen:
            seen.add(idx)
            picks.append(pool[idx])
        idx = (idx + stride) % len(pool)
    return picks


def follow_up_pool_size(task_number: int) -> int:
    """Return the size of the local stub pool for `task_number`.

    The audit (`phase5_audit.md §14`) asserts this is ≥ 8 for every
    task that has follow-ups (Tasks 1 and 3).
    """
    return len(_FOLLOW_UP_POOL.get(task_number, ()))


__all__ = ["follow_up_pool_size", "sample_follow_ups"]
