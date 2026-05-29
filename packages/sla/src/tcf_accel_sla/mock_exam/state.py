"""Mock-exam state machine.

Implements the SCHEDULED → CO_ACTIVE → … → SCORED / FORFEITED graph
from `phase6_design.md §3`. The transition function is pure: given
`(current_state, event, mode, now, started_at)`, it returns the new
state or raises `InvalidMockTransitionError`.

State lives in the API layer (`apps/api/.../mock_exam_state.py`);
this module is just the algebra plus the journal record shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final, Literal

from tcf_accel.ids import MockExamId
from tcf_accel.schemas.item import Module


class MockState(str, Enum):
    """The full state lattice for one mock exam.

    `_DONE` states are transient: the API immediately advances them to
    the corresponding `BREAK_n`. They exist so the journal records the
    moment the module finished — useful for the "did you submit early
    or hit the timer?" forensic question.
    """

    SCHEDULED = "SCHEDULED"
    STARTED = "STARTED"
    CO_ACTIVE = "CO_ACTIVE"
    CO_DONE = "CO_DONE"
    BREAK_1 = "BREAK_1"
    CE_ACTIVE = "CE_ACTIVE"
    CE_DONE = "CE_DONE"
    BREAK_2 = "BREAK_2"
    EE_ACTIVE = "EE_ACTIVE"
    EE_DONE = "EE_DONE"
    BREAK_3 = "BREAK_3"
    EO_ACTIVE = "EO_ACTIVE"
    EO_DONE = "EO_DONE"
    FINISHED = "FINISHED"
    SCORED = "SCORED"
    FORFEITED = "FORFEITED"


MockExamMode = Literal["canonical", "training"]

MockEvent = Literal[
    "start",
    "advance",           # learner-or-timer advancing past the current state
    "submit_final",      # submit at the end of EO
    "score_complete",    # the worker finished scoring
    "tab_blur_exceeded", # tab-blur > grace in canonical mode
    "process_abort",     # API/process crash in canonical mode
]

# Which BREAK follows which _DONE state.
BREAK_AFTER: Final[dict[MockState, MockState]] = {
    MockState.CO_DONE: MockState.BREAK_1,
    MockState.CE_DONE: MockState.BREAK_2,
    MockState.EE_DONE: MockState.BREAK_3,
}

# Linear "advance" order. Every non-final state has exactly one
# successor under the `advance` event.
_ADVANCE_ORDER: Final[list[MockState]] = [
    MockState.SCHEDULED,
    MockState.STARTED,
    MockState.CO_ACTIVE,
    MockState.CO_DONE,
    MockState.BREAK_1,
    MockState.CE_ACTIVE,
    MockState.CE_DONE,
    MockState.BREAK_2,
    MockState.EE_ACTIVE,
    MockState.EE_DONE,
    MockState.BREAK_3,
    MockState.EO_ACTIVE,
    MockState.EO_DONE,
    MockState.FINISHED,
    MockState.SCORED,
]

_TERMINAL: Final[frozenset[MockState]] = frozenset(
    {MockState.SCORED, MockState.FORFEITED},
)

_FORFEITABLE: Final[frozenset[MockState]] = frozenset(
    s for s in MockState if s not in _TERMINAL and s != MockState.FINISHED
)


class InvalidMockTransitionError(Exception):
    """Raised when a transition is not permitted by the state machine."""


@dataclass(frozen=True)
class MockJournalEntry:
    """One audit entry written on every state transition.

    The journal is replayable: walking the entries reconstructs the
    exact lifecycle of a mock, which is the primary forensic tool for
    "was this forfeit legitimate?" investigations.
    """

    mock_id: MockExamId
    at: datetime
    from_state: MockState
    to_state: MockState
    reason: str
    elapsed_s_in_state: float


def next_module(after: MockState) -> Module | None:
    """Return the next *active* module after `after`, or None at the end.

    Used by the API's `advance` handler to figure out which module's
    items to expose next. None means "the mock is over; submit."

    Example:
        >>> next_module(MockState.BREAK_1)
        'CE'
        >>> next_module(MockState.BREAK_3)
        'EO'
        >>> next_module(MockState.EO_DONE) is None
        True
    """
    mapping: dict[MockState, Module] = {
        MockState.STARTED: "CO",
        MockState.BREAK_1: "CE",
        MockState.BREAK_2: "EE",
        MockState.BREAK_3: "EO",
    }
    return mapping.get(after)


def transition(
    current: MockState,
    event: MockEvent,
    *,
    mode: MockExamMode,
) -> MockState:
    """Compute the next state.

    Pure function; raises `InvalidMockTransitionError` for impossible
    transitions. The API layer maps the exception to a 409 with the
    `MockInvalidTransitionError` code.

    Args:
        current: The mock's current state.
        event: The driving event.
        mode: "canonical" or "training" — only `mode == "canonical"`
            permits the `tab_blur_exceeded` and `process_abort` events
            to forfeit. In training mode those events are no-ops (the
            caller is expected to pause + resume instead).

    Returns:
        The next `MockState`.
    """
    if current in _TERMINAL:
        msg = f"cannot transition from terminal state {current}"
        raise InvalidMockTransitionError(msg)

    if event == "start":
        if current != MockState.SCHEDULED:
            msg = f"`start` requires SCHEDULED, got {current}"
            raise InvalidMockTransitionError(msg)
        return MockState.STARTED

    if event == "advance":
        try:
            idx = _ADVANCE_ORDER.index(current)
        except ValueError as exc:
            msg = f"`advance` not defined from {current}"
            raise InvalidMockTransitionError(msg) from exc
        if current == MockState.STARTED:
            return MockState.CO_ACTIVE
        if current == MockState.FINISHED:
            msg = "`advance` from FINISHED is illegal; await `score_complete`."
            raise InvalidMockTransitionError(msg)
        if idx + 1 >= len(_ADVANCE_ORDER):
            msg = f"no successor for {current}"
            raise InvalidMockTransitionError(msg)
        return _ADVANCE_ORDER[idx + 1]

    if event == "submit_final":
        if current != MockState.EO_ACTIVE and current != MockState.EO_DONE:
            msg = f"`submit_final` requires EO_ACTIVE or EO_DONE, got {current}"
            raise InvalidMockTransitionError(msg)
        return MockState.FINISHED

    if event == "score_complete":
        if current != MockState.FINISHED:
            msg = f"`score_complete` requires FINISHED, got {current}"
            raise InvalidMockTransitionError(msg)
        return MockState.SCORED

    if event in ("tab_blur_exceeded", "process_abort"):
        if mode != "canonical":
            # Training mode never forfeits; the caller pauses + resumes
            # via a separate code path.
            return current
        if current not in _FORFEITABLE:
            msg = f"cannot forfeit from {current}"
            raise InvalidMockTransitionError(msg)
        return MockState.FORFEITED

    msg = f"unknown event {event}"
    raise InvalidMockTransitionError(msg)


def is_terminal(state: MockState) -> bool:
    """True iff the mock has reached SCORED or FORFEITED."""
    return state in _TERMINAL


def is_active(state: MockState) -> bool:
    """True iff the mock is in one of the `*_ACTIVE` states."""
    return state in {
        MockState.CO_ACTIVE,
        MockState.CE_ACTIVE,
        MockState.EE_ACTIVE,
        MockState.EO_ACTIVE,
    }


__all__ = [
    "BREAK_AFTER",
    "InvalidMockTransitionError",
    "MockEvent",
    "MockExamMode",
    "MockJournalEntry",
    "MockState",
    "is_active",
    "is_terminal",
    "next_module",
    "transition",
]
