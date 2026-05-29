"""Mock-exam state machine — every legal transition; every illegal one raises."""

from __future__ import annotations

import pytest

from tcf_accel_sla.mock_exam import (
    BREAK_AFTER,
    MockState,
    next_module,
    transition,
)
from tcf_accel_sla.mock_exam.state import (
    InvalidMockTransitionError,
    is_active,
    is_terminal,
)


def test_start_from_scheduled() -> None:
    assert transition(MockState.SCHEDULED, "start", mode="canonical") == MockState.STARTED


def test_advance_walk_to_eo_active() -> None:
    state = MockState.STARTED
    sequence = []
    for _ in range(20):
        if state == MockState.FINISHED:
            break
        try:
            state = transition(state, "advance", mode="canonical")
        except InvalidMockTransitionError:
            break
        sequence.append(state)
    # Must traverse CO_ACTIVE → CE_ACTIVE → EE_ACTIVE → EO_ACTIVE → FINISHED.
    actives = [s for s in sequence if is_active(s)]
    assert actives == [
        MockState.CO_ACTIVE,
        MockState.CE_ACTIVE,
        MockState.EE_ACTIVE,
        MockState.EO_ACTIVE,
    ]


def test_advance_passes_through_each_done_and_break() -> None:
    state = MockState.STARTED
    seen: list[MockState] = []
    for _ in range(30):
        state = transition(state, "advance", mode="canonical")
        seen.append(state)
        if state == MockState.FINISHED:
            break
    # Every DONE state and every BREAK state appears.
    for done in (MockState.CO_DONE, MockState.CE_DONE, MockState.EE_DONE, MockState.EO_DONE):
        assert done in seen
    for brk in (MockState.BREAK_1, MockState.BREAK_2, MockState.BREAK_3):
        assert brk in seen


def test_submit_final_from_eo_active() -> None:
    assert (
        transition(MockState.EO_ACTIVE, "submit_final", mode="canonical")
        == MockState.FINISHED
    )


def test_submit_final_from_eo_done() -> None:
    assert (
        transition(MockState.EO_DONE, "submit_final", mode="canonical")
        == MockState.FINISHED
    )


def test_submit_final_from_co_is_invalid() -> None:
    with pytest.raises(InvalidMockTransitionError):
        transition(MockState.CO_ACTIVE, "submit_final", mode="canonical")


def test_score_complete_from_finished() -> None:
    assert (
        transition(MockState.FINISHED, "score_complete", mode="canonical")
        == MockState.SCORED
    )


def test_tab_blur_canonical_forfeits() -> None:
    assert (
        transition(MockState.CO_ACTIVE, "tab_blur_exceeded", mode="canonical")
        == MockState.FORFEITED
    )


def test_tab_blur_training_is_noop() -> None:
    assert (
        transition(MockState.CO_ACTIVE, "tab_blur_exceeded", mode="training")
        == MockState.CO_ACTIVE
    )


def test_process_abort_canonical_forfeits() -> None:
    assert (
        transition(MockState.BREAK_2, "process_abort", mode="canonical")
        == MockState.FORFEITED
    )


def test_no_transition_from_terminal() -> None:
    for terminal in (MockState.SCORED, MockState.FORFEITED):
        with pytest.raises(InvalidMockTransitionError):
            transition(terminal, "advance", mode="canonical")


def test_is_terminal_only_for_scored_and_forfeited() -> None:
    assert is_terminal(MockState.SCORED)
    assert is_terminal(MockState.FORFEITED)
    assert not is_terminal(MockState.CO_ACTIVE)
    assert not is_terminal(MockState.FINISHED)


def test_next_module_mapping() -> None:
    assert next_module(MockState.STARTED) == "CO"
    assert next_module(MockState.BREAK_1) == "CE"
    assert next_module(MockState.BREAK_2) == "EE"
    assert next_module(MockState.BREAK_3) == "EO"
    assert next_module(MockState.EO_DONE) is None


def test_break_after_map_is_complete() -> None:
    assert BREAK_AFTER == {
        MockState.CO_DONE: MockState.BREAK_1,
        MockState.CE_DONE: MockState.BREAK_2,
        MockState.EE_DONE: MockState.BREAK_3,
    }
