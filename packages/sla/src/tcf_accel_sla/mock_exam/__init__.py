"""Mock exam engine — Phase 6 (`06_MOCK_EXAM_ENGINE.md`).

Re-exports the public surface used by the API route + worker layers.
The engine is pure-Python (no native deps); ADR-035 records the
rejection of OR-Tools.

Submodules:

- `tcf_accel_sla.mock_exam.spec` — exam-shape constants.
- `tcf_accel_sla.mock_exam.state` — state machine + transitions.
- `tcf_accel_sla.mock_exam.cadence` — week-aware cooldown cap.
- `tcf_accel_sla.mock_exam.selector` — constraint-guided item selector.
- `tcf_accel_sla.mock_exam.scorer` — per-skill scoring + divergence.
- `tcf_accel_sla.mock_exam.report` — Markdown + HTML renderer.
- `tcf_accel_sla.mock_exam.candidate` — scripted-candidate integration test driver.
"""

from __future__ import annotations

from tcf_accel_sla.mock_exam.cadence import (
    MOCK_CADENCE_TABLE,
    can_start_canonical,
    can_start_training,
    mocks_allowed_per_iso_week,
    week_index_since,
)
from tcf_accel_sla.mock_exam.candidate import (
    CandidateProfile,
    CandidateRunner,
    CandidateRunResult,
    DEFAULT_P_CORRECT,
    DEFAULT_RUBRIC_BY_TASK,
    expected_active_seconds,
)
from tcf_accel_sla.mock_exam.report import (
    MockExamReportFull,
    booking_advice,
    render_html,
    render_markdown,
)
from tcf_accel_sla.mock_exam.scorer import (
    ItemOutcome,
    MockSkillScore,
    RubricOutcome,
    composite_nclc,
    divergence_alert,
    score_mock,
)
from tcf_accel_sla.mock_exam.selector import (
    PooledMockItem,
    SelectorInputs,
    SelectorResult,
    select_for_module,
    select_full_mock,
)
from tcf_accel_sla.mock_exam.spec import (
    ACTIVE_DURATION_S,
    BREAK_DURATION_S,
    CANONICAL_TAB_BLUR_GRACE_S,
    EXAM_SHAPE,
    FEI_SPREAD,
    MODULE_DURATION_S,
    MODULE_ORDER,
    TOTAL_DURATION_S,
)
from tcf_accel_sla.mock_exam.state import (
    BREAK_AFTER,
    MockEvent,
    MockExamMode,
    MockJournalEntry,
    MockState,
    next_module,
    transition,
)

__all__ = [
    "ACTIVE_DURATION_S",
    "BREAK_AFTER",
    "BREAK_DURATION_S",
    "CANONICAL_TAB_BLUR_GRACE_S",
    "CandidateProfile",
    "CandidateRunner",
    "CandidateRunResult",
    "DEFAULT_P_CORRECT",
    "DEFAULT_RUBRIC_BY_TASK",
    "EXAM_SHAPE",
    "FEI_SPREAD",
    "MOCK_CADENCE_TABLE",
    "MODULE_DURATION_S",
    "MODULE_ORDER",
    "MockEvent",
    "MockExamMode",
    "MockExamReportFull",
    "MockJournalEntry",
    "MockSkillScore",
    "MockState",
    "ItemOutcome",
    "PooledMockItem",
    "RubricOutcome",
    "SelectorInputs",
    "SelectorResult",
    "TOTAL_DURATION_S",
    "booking_advice",
    "can_start_canonical",
    "can_start_training",
    "composite_nclc",
    "divergence_alert",
    "expected_active_seconds",
    "mocks_allowed_per_iso_week",
    "next_module",
    "render_html",
    "render_markdown",
    "score_mock",
    "select_for_module",
    "select_full_mock",
    "transition",
    "week_index_since",
]
