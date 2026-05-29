"""Practice-session logic (`phase5_design.md §3`, §8).

Phase 5 hosts the *pure* session logic here — the exam-shape floor
(ADR-028) and its rolling-window computation. The stateful
orchestration (the session store, the item queue) lives in the API
layer (`apps/api/.../session_state.py`), mirroring how Phase 4 kept the
diagnostic store in the API while the CAT math lived in
`tcf_accel_sla.diagnostic`. This keeps `packages/sla` zero-runtime-
dependency.
"""

from __future__ import annotations

from tcf_accel_sla.session.exam_shape_floor import (
    EXAM_SHAPE_DRILL_TYPES,
    EXAM_SHAPE_FLOOR_LOWER,
    EXAM_SHAPE_FLOOR_MIN,
    SessionRecord,
    floor_satisfied,
    is_exam_shape_drill,
    iso_week,
    rolling_7d_exam_shape_minutes,
)

__all__ = [
    "EXAM_SHAPE_DRILL_TYPES",
    "EXAM_SHAPE_FLOOR_LOWER",
    "EXAM_SHAPE_FLOOR_MIN",
    "SessionRecord",
    "floor_satisfied",
    "is_exam_shape_drill",
    "iso_week",
    "rolling_7d_exam_shape_minutes",
]
