"""`/v1/session/*` — practice session lifecycle (Phase 5).

Thin HTTP layer over the drill engine (`tcf_accel_sla.drills`) and the
exam-shape floor (`tcf_accel_sla.session`). Persistence is the
in-process store in `tcf_accel_api.session_state` (Phase 5's later step
swaps to Postgres). The item source is the synthetic
`tcf_accel_api.session_pool` (the real bank + scheduler integration is
deferred with the Postgres swap).

The drill loop (`phase5_design.md §3`):
    start → next → answer → … → finish
with pause/resume (≤ 24 h) and a dismiss endpoint for the exam-shape
floor (ADR-028).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from tcf_accel.errors import (
    DrillInputInvalidError,
    ExamShapeFloorViolation,
    PauseWindowExpiredError,
)
from tcf_accel.ids import SessionId, UserId
from tcf_accel.schemas.api.session import (
    SessionAnswer,
    SessionItem,
    SessionStart,
    SessionState,
    SessionSummary,
    SkillDelta,
)
from tcf_accel_sla.drills import get_drill, resolve_drill_kind
from tcf_accel_sla.estimator import update_with_mcq
from tcf_accel_sla.session import (
    EXAM_SHAPE_FLOOR_MIN,
    floor_satisfied,
    is_exam_shape_drill,
)

from tcf_accel_api.session_pool import find_pooled, pooled_items_for
from tcf_accel_api.session_state import (
    PracticeSession,
    dismissed_this_week,
    get_session,
    put_session,
    record_dismissal,
    session_records,
)
from tcf_accel_api.state import current_user_id, get_user_state

router = APIRouter(prefix="/v1/session", tags=["session"])

_PAUSE_WINDOW = timedelta(hours=24)
_DEFAULT_QUEUE_LEN = 10


def _project_state(session: PracticeSession) -> SessionState:
    return SessionState(
        id=session.id,
        user_id=session.user_id,
        module=session.module,
        drill_type=session.drill_type,
        target_minutes=session.target_minutes,
        started_at=session.started_at,
        finished_at=session.finished_at,
        items_seen=session.items_seen,
        items_correct=session.items_correct,
    )


def _build_queue(user_id: UserId, module: str, mean: float) -> list[UUID]:
    """Order the module's pooled items by proximity to the posterior mean.

    A crude stand-in for the FSRS/CAT scheduler: serve the items whose
    difficulty is nearest the learner's current estimate (Krashen i+1),
    capped at `_DEFAULT_QUEUE_LEN`.
    """
    pooled = pooled_items_for(module)  # type: ignore[arg-type]
    pooled.sort(key=lambda p: abs(p.difficulty - mean))
    return [p.item.id for p in pooled[:_DEFAULT_QUEUE_LEN]]


@router.post(
    "/start",
    response_model=SessionState,
    status_code=201,
    summary="Start a practice session",
)
async def start(
    body: SessionStart,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> SessionState:
    """Initialize a session with the requested module and drill type.

    Enforces the exam-shape floor (ADR-028): a non-exam-shape drill is
    refused with 409 if the learner has logged zero exam-shape minutes
    in the rolling 7-day window and has not dismissed the floor this
    week.
    """
    now = datetime.now(UTC)
    exam_shape = is_exam_shape_drill(body.drill_type)

    if not exam_shape and not floor_satisfied(
        session_records(user_id),
        now=now,
        dismissed_this_week=dismissed_this_week(user_id, now=now),
    ):
        err = ExamShapeFloorViolation(minutes=0, floor=EXAM_SHAPE_FLOOR_MIN)
        raise HTTPException(
            status_code=err.http_status,
            detail={
                **err.to_envelope(),
                "next_action": "exam_shape",
                "suggested_drill_types": ["mock_section", "ee_task"],
                "dismissable": True,
            },
        )

    state = get_user_state(user_id)
    try:
        drill_kind = resolve_drill_kind(body.module, body.drill_type)
        # ADR-029: when the learner has opted into the CO accessibility
        # alternative, swap the requested CO drill for `co_lexical_alt`
        # *before* the registry lookup — the swap is a session-time
        # routing decision, not a drill-kind override the client sends.
        if body.module == "CO" and state.accessibility.co_alternative == "lexical_alt":
            drill_kind = "co_lexical_alt"
        # Symmetric EO accessibility (`phase5_design.md §7.2`): a
        # learner opted into `text_input` gets `eo_text_alt`, which
        # emits `module=EE` — same shape as the CO case.
        if body.module == "EO" and state.accessibility.eo_alternative == "text_input":
            drill_kind = "eo_text_alt"
        drill = get_drill(drill_kind)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    # The session may visually be a CO session (the user asked for CO),
    # but `co_lexical_alt` updates the CE posterior — `posterior_skill`
    # is the source of truth for snapshot/delta in finish.
    posterior_skill = drill.spec.module
    mean = state.posteriors[posterior_skill].mean
    queue = _build_queue(user_id, body.module, state.posteriors[body.module].mean)

    session = PracticeSession(
        id=SessionId(uuid4()),
        user_id=user_id,
        module=body.module,
        drill_type=body.drill_type,
        drill_kind=drill_kind,
        posterior_skill=posterior_skill,
        target_minutes=body.target_minutes,
        exam_shape=exam_shape,
        started_at=now,
        queue=queue,
        start_posterior_mean=mean,
    )
    put_session(user_id, session)
    return _project_state(session)


@router.get(
    "/{session_id}/next",
    response_model=SessionItem,
    summary="Fetch the next item per the scheduler",
)
async def next_item(
    session_id: UUID,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> SessionItem:
    """Serve the next unanswered item; 409 once the queue is exhausted."""
    session = _require_active(user_id, session_id)
    if session.cursor >= len(session.queue):
        raise HTTPException(
            status_code=409,
            detail="Session queue exhausted; call /finish.",
        )
    item_id = session.queue[session.cursor]
    pooled = find_pooled(item_id)
    if pooled is None:  # pragma: no cover - pool is deterministic
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found.")
    session.pending_item_id = item_id
    drill = get_drill(session.drill_kind)
    step = drill.present(pooled.item)
    return SessionItem(
        session_id=session.id,
        item=pooled.item,
        is_review=False,
        expected_rt_ms=step.expected_rt_ms,
    )


@router.post(
    "/{session_id}/answer",
    response_model=SessionState,
    summary="Submit an answer mid-session",
)
async def answer(
    session_id: UUID,
    body: SessionAnswer,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> SessionState:
    """Grade an answer, update the posterior, and advance the session.

    Idempotent on `item_id`: a duplicate submission returns the current
    state without re-grading (matches `phase5_design.md §3.2`).
    """
    session = _require_active(user_id, session_id)
    item_uuid = UUID(str(body.item_id))

    if item_uuid in session.answered:
        return _project_state(session)  # idempotent replay

    pooled = find_pooled(item_uuid)
    if pooled is None:
        err = DrillInputInvalidError(detail=f"Item {body.item_id} not in pool.")
        raise HTTPException(status_code=err.http_status, detail=err.to_envelope())

    drill = get_drill(session.drill_kind)
    result = drill.grade(pooled.item, body.response)

    # Update the per-skill posterior (the drill's declared module, which
    # for co_lexical_alt is CE, not CO — ADR-029).
    state = get_user_state(user_id)
    skill = drill.spec.module
    prior = state.posteriors[skill]
    state.posteriors[skill] = update_with_mcq(
        prior,
        item_difficulty=pooled.difficulty,
        discrimination=pooled.discrimination,
        correct=bool(result.correct),
    )

    session.items_seen += 1
    session.items_correct += int(bool(result.correct))
    session.answered.add(item_uuid)
    session.pending_item_id = None
    if session.cursor < len(session.queue) and session.queue[session.cursor] == item_uuid:
        session.cursor += 1
    return _project_state(session)


@router.post(
    "/{session_id}/finish",
    response_model=SessionSummary,
    summary="Close the session and commit FSRS state",
)
async def finish(
    session_id: UUID,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> SessionSummary:
    """Close the session and return the summary with the posterior delta."""
    session = get_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.finished_at is None:
        session.finished_at = datetime.now(UTC)

    state = get_user_state(user_id)
    after = state.posteriors[session.posterior_skill].mean
    accuracy = session.items_correct / session.items_seen if session.items_seen else 0.0
    delta = SkillDelta(
        skill=session.posterior_skill,
        before=session.start_posterior_mean,
        after=after,
        delta=after - session.start_posterior_mean,
    )
    return SessionSummary(
        session_id=session.id,
        finished_at=session.finished_at,
        items_seen=session.items_seen,
        items_correct=session.items_correct,
        accuracy=accuracy,
        deltas=[delta],
        cards_due_next_24h=0,  # FSRS card persistence lands with the bank swap
        plan_regenerated=False,
    )


@router.post(
    "/{session_id}/pause",
    response_model=SessionState,
    summary="Pause a session (resumable within 24h)",
)
async def pause(
    session_id: UUID,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> SessionState:
    """Pause an in-flight session."""
    session = _require_active(user_id, session_id)
    session.paused_at = datetime.now(UTC)
    return _project_state(session)


@router.post(
    "/{session_id}/resume",
    response_model=SessionState,
    summary="Resume a paused session (410 if the 24h window expired)",
)
async def resume(
    session_id: UUID,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> SessionState:
    """Resume a paused session; 410 if more than 24 h elapsed."""
    session = get_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.finished_at is not None:
        raise HTTPException(status_code=409, detail="Session already finished.")
    if session.paused_at is not None:
        elapsed = datetime.now(UTC) - session.paused_at
        if elapsed > _PAUSE_WINDOW:
            err = PauseWindowExpiredError(hours=round(elapsed.total_seconds() / 3600, 1))
            raise HTTPException(status_code=err.http_status, detail=err.to_envelope())
        session.paused_at = None
    return _project_state(session)


@router.post(
    "/exam-shape/dismiss",
    status_code=200,
    summary="Dismiss the exam-shape floor for the current ISO week (ADR-028)",
)
async def dismiss_exam_shape(
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> dict[str, str]:
    """Record an exam-shape-floor dismissal for the current ISO week.

    The dismissal is logged (local-only per ADR-017) and lets the
    learner start non-exam-shape drills for the rest of the week. The
    operator's `audit-exam-shape` flags chronic dismissals.
    """
    week = record_dismissal(user_id, now=datetime.now(UTC))
    return {"dismissed_week": week, "status": "ok"}


def _require_active(user_id: UserId, session_id: UUID) -> PracticeSession:
    """Fetch a session that exists, is not finished, and is not paused."""
    session = get_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.finished_at is not None:
        raise HTTPException(status_code=409, detail="Session already finished.")
    if session.paused_at is not None:
        raise HTTPException(status_code=409, detail="Session is paused; call /resume.")
    return session
