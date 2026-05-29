"""Drill engine base types and the `Drill` protocol (`phase5_design.md §3.1`).

`DrillSpec` is static metadata about a drill kind (which posterior it
updates, whether it records audio, its exam-pace budget). `DrillStep`
is the per-item presentation state handed to the UI. `DrillResult` is
the graded outcome. `Drill.to_interaction` is the single funnel into
the `interactions` table.

The base also hosts `grade_mcq`, the shared MCQ grading used by `co_mcq`
and `ce_mcq` (and, later, the per-question aggregation in gap-fill /
connector drills).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from tcf_accel.schemas.api.plan import DrillKind
from tcf_accel.schemas.content import MCQ
from tcf_accel.schemas.interaction import Interaction
from tcf_accel.schemas.item import Item, Module
from tcf_accel.schemas.pronunciation import PronunciationSignal


@dataclass(frozen=True)
class DrillSpec:
    """Static description of a drill kind.

    `module` is the posterior the drill's interactions update — which is
    *not* always the module the drill visually resembles: the CO
    accessibility alternative (`co_lexical_alt`) declares `module="CE"`
    so its interactions never reach the CO posterior (ADR-029).
    """

    drill_kind: DrillKind
    module: Module
    requires_audio_in: bool = False
    requires_audio_out: bool = False
    single_play: bool = False
    exam_pace_default_s_per_item: int | None = None
    accessibility_alt: DrillKind | None = None
    rubric_pending: bool = False


@dataclass(frozen=True)
class DrillStep:
    """Presentation state for one item, handed to the UI.

    `payload` carries drill-specific hints (e.g. `n_gaps`, `expose_ms`,
    `prep_time_s`). `single_play` echoes the spec so the player can
    enforce the no-replay contract for CO (ADR-029).
    """

    item_id: UUID
    drill_kind: DrillKind
    single_play: bool = False
    expected_rt_ms: int | None = None
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DrillResult:
    """Graded outcome of one drill step.

    `correct` is `None` for rubric-pending drills (EE/EO) where the
    async scorer (Phase 7) decides correctness later. `partial_credit`
    is the [0, 1] fraction for multi-part drills (gap-fill, skim-scan).
    """

    correct: bool | None
    partial_credit: float | None = None
    raw_response: dict[str, object] = field(default_factory=dict)
    pronunciation: PronunciationSignal | None = None
    graded_score: dict[str, object] | None = None


def grade_mcq(question: MCQ, response: dict[str, object]) -> bool:
    """Grade a single MCQ response.

    The response carries the chosen option id under either `option_id`
    or `answer` (the golden-learner fixture uses `answer`; the
    `SessionAnswer` wire uses an open dict). A missing or unrecognized
    option grades as incorrect rather than raising — a learner who
    times out submits no option, which is a wrong answer, not an error.

    Example:
        >>> from tcf_accel.schemas.content import MCQ, MCQOption
        >>> q = MCQ(
        ...     id="q1",
        ...     prompt="?",
        ...     options=[MCQOption(id="a", text="x"), MCQOption(id="b", text="y")],
        ...     correct_option_id="a",
        ... )
        >>> grade_mcq(q, {"option_id": "a"})
        True
        >>> grade_mcq(q, {"answer": "b"})
        False
        >>> grade_mcq(q, {})
        False

    Complexity: O(1).
    """
    chosen = response.get("option_id")
    if chosen is None:
        chosen = response.get("answer")
    return chosen == question.correct_option_id


class Drill(ABC):
    """One drill kind. Subclasses are stateless; all state is in args.

    The lifecycle (`tcf_accel_sla.session.lifecycle`) calls
    `present` → (UI) → `grade` → `to_interaction` for each item.
    """

    spec: DrillSpec

    @abstractmethod
    def present(self, item: Item) -> DrillStep:
        """Build the presentation state for `item`."""
        raise NotImplementedError

    @abstractmethod
    def grade(self, item: Item, response: dict[str, object]) -> DrillResult:
        """Grade a learner `response` against `item`."""
        raise NotImplementedError

    def to_interaction(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        item: Item,
        result: DrillResult,
        rt_ms: int | None,
        rating: int | None,
        created_at: datetime,
    ) -> Interaction:
        """Project a graded result into the typed `Interaction` row.

        The single funnel into the learner model. The `module` written
        is the *drill's declared module* (`self.spec.module`), not the
        item's — this is what lets `co_lexical_alt` (a CO-shaped drill
        declared `module="CE"`) keep its interactions out of the CO
        posterior (ADR-029).
        """
        return Interaction(
            user_id=user_id,
            item_id=item.id,
            session_id=session_id,
            module=self.spec.module,
            correct=result.correct,
            raw_response=result.raw_response,
            rt_ms=rt_ms,
            rating=rating,
            graded_score=result.graded_score,
            drill_kind=self.spec.drill_kind,
            pronunciation=result.pronunciation,
            audio_path=None,  # local-only retention is an operator opt-in (ADR-017)
            created_at=created_at,
        )


__all__ = ["Drill", "DrillResult", "DrillSpec", "DrillStep", "grade_mcq"]
