"""The quality gate (`phase3_design.md §5`).

`gate.py` (Phase 3 implementation) runs the 13 checks in cheapest-first
order and emits a `QualityReport`. The checks themselves live in
sibling files: `pii.py`, `adversarial.py`, `length.py`,
`duplicates.py`, `license.py`, etc.

P0 failures → reject. P1 failures → pass-with-flag, routed to the
manual-review queue.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from tcf_accel.schemas import Item

from tcf_accel_content.types import QualityCheckResult, QualityReport

GateVerdict = Literal["pass", "p1_flag", "reject"]


@runtime_checkable
class QualityCheck(Protocol):
    """One named gate check.

    Implementations declare `name` and `severity` and run as a callable
    over an `Item`. Stateless; gates are composed by `gate.run_gate`.
    """

    name: str
    severity: Literal["P0", "P1"]

    def __call__(self, item: Item) -> QualityCheckResult:
        """Run the check on one item and return its `QualityCheckResult`."""
        ...


# Tunable thresholds from the design doc + ADRs. Re-export so the
# gate implementation and the tests can import a single source.
ADVERSARIAL_THRESHOLD: float = 0.25  # ADR-0019
ADVERSARIAL_TRIALS: int = 20  # ADR-0019
DISTRACTOR_LENGTH_TOLERANCE: float = 0.25  # phase3_design.md §5.3
CEFR_CONFIDENCE_FLOOR: float = 0.65  # phase3_design.md §4.5
DUPLICATE_SIMILARITY_THRESHOLD: float = 0.92  # phase3_design.md §5.6


__all__ = [
    "ADVERSARIAL_THRESHOLD",
    "ADVERSARIAL_TRIALS",
    "CEFR_CONFIDENCE_FLOOR",
    "DISTRACTOR_LENGTH_TOLERANCE",
    "DUPLICATE_SIMILARITY_THRESHOLD",
    "GateVerdict",
    "QualityCheck",
    "QualityCheckResult",
    "QualityReport",
]
