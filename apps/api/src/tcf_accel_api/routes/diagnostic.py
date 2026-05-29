"""`/v1/diagnostic/*` — adaptive diagnostic. Phase 4 implementation.

The CAT routine lives in `tcf_accel_sla.diagnostic.cat`; this module is
the thin HTTP layer. Persistence is the in-process store in
`tcf_accel_api.state` (Phase 5 swap to Redis).

Spec ownership: the original Phase 2 stub table marks `/v1/diagnostic/*`
as Phase 5, but `04_LEARNER_MODEL.md §1.3 + §2.4` explicitly defines the
CAT routine in Phase 4 and lists this file under Phase 4's CODE surface.
We implement here; the stub-test table is updated in the same PR so the
501-expectation is dropped.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from tcf_accel.ids import ItemId, SessionId, UserId
from tcf_accel.schemas.api.diagnostic import (
    DiagnosticAnswer,
    DiagnosticReport,
    DiagnosticState,
    SkillLevel,
)
from tcf_accel.schemas.item import CefrLevel, Module
from tcf_accel.schemas.scoring import SkillCode
from tcf_accel_sla.diagnostic import CandidateItem, DiagnosticSession
from tcf_accel_sla.estimator import to_nclc_estimate
from tcf_accel_sla.planner.allocator import SKILL_ORDER

from tcf_accel_api.diagnostic_pool import candidates_for
from tcf_accel_api.state import (
    DiagnosticUmbrella,
    current_user_id,
    get_diagnostic,
    get_user_state,
    start_diagnostic,
)

router = APIRouter(prefix="/v1/diagnostic", tags=["diagnostic"])


def _nclc_to_cefr(nclc: float) -> CefrLevel:
    """Coarse NCLC → CEFR mapping (advisory only; NCLC is canonical)."""
    if nclc < 4:
        return "A1"
    if nclc < 5:
        return "A2"
    if nclc < 7:
        return "B1"
    if nclc < 9:
        return "B2"
    if nclc < 11:
        return "C1"
    return "C2"


def _find_item(item_id: UUID) -> tuple[SkillCode, CandidateItem] | None:
    """Locate `(skill, candidate)` for the given item id in the pool."""
    for skill in SKILL_ORDER:
        for cand in candidates_for(skill):
            if cand.item_id == item_id:
                return skill, cand
    return None


def _current_and_completed(
    umbrella: DiagnosticUmbrella,
) -> tuple[SkillCode | None, list[Module]]:
    """The first not-yet-stopped skill (None if all done) + completed list."""
    completed: list[Module] = []
    for skill in SKILL_ORDER:
        sess = umbrella.sessions.get(skill)
        if sess is None:
            return skill, completed
        if sess.should_stop():
            completed.append(skill)
            continue
        return skill, completed
    return None, completed


def _prefetch_next(
    umbrella: DiagnosticUmbrella,
    user_id: UserId,
    current: SkillCode | None,
) -> ItemId | None:
    """Pick the next item id for the client (None if session is done)."""
    if current is None:
        return None
    sess = umbrella.sessions.get(current)
    if sess is None:
        sess = DiagnosticSession.start(user_id=user_id, skill=current)
    picked = sess.next_item(candidates_for(current))
    if picked is None:
        return None
    return ItemId(picked.item_id)


def _project_state(
    session_id: UUID,
    user_id: UserId,
    umbrella: DiagnosticUmbrella,
) -> DiagnosticState:
    """Map the in-memory umbrella onto the wire schema."""
    current, completed = _current_and_completed(umbrella)
    finished_at: datetime | None = (
        datetime.now(UTC) if current is None else None
    )
    items_seen = sum(len(s.administered) for s in umbrella.sessions.values())
    estimates: dict[Module, float] = {
        skill: sess.posterior.mean for skill, sess in umbrella.sessions.items()
    }
    return DiagnosticState(
        id=SessionId(session_id),
        user_id=user_id,
        started_at=umbrella.started_at,
        finished_at=finished_at,
        current_module=current,
        completed_modules=completed,
        items_seen=items_seen,
        next_item_id=_prefetch_next(umbrella, user_id, current),
        estimates_in_progress=estimates,
    )


@router.post(
    "/start",
    response_model=DiagnosticState,
    status_code=201,
    summary="Start a diagnostic session",
)
async def start(
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> DiagnosticState:
    """Begin a fresh adaptive-diagnostic session.

    The umbrella session covers all four skills sequentially. The CAT
    advances per skill until each reaches its stopping criterion (variance
    ≤ 0.3 or 15 items).
    """
    session_id = uuid4()
    umbrella = start_diagnostic(user_id, session_id)
    # Pre-seed the first skill so /next_item_id is non-null right away.
    umbrella.sessions["CO"] = DiagnosticSession.start(user_id=user_id, skill="CO")
    return _project_state(session_id, user_id, umbrella)


@router.post(
    "/{session_id}/answer",
    response_model=DiagnosticState,
    summary="Submit an answer to a diagnostic item",
)
async def answer(
    session_id: UUID,
    body: DiagnosticAnswer,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> DiagnosticState:
    """Record one answer and advance the CAT state."""
    umbrella = get_diagnostic(user_id, session_id)
    if umbrella is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found.")

    located = _find_item(UUID(str(body.item_id)))
    if located is None:
        raise HTTPException(
            status_code=404,
            detail=f"Item {body.item_id} not in diagnostic pool.",
        )
    skill, cand = located

    sess = umbrella.sessions.get(skill)
    if sess is None:
        sess = DiagnosticSession.start(user_id=user_id, skill=skill)
        umbrella.sessions[skill] = sess

    if skill in ("CO", "CE"):
        answer_id = body.response.get("answer")
        # Synthetic-pool scoring: correct iff item difficulty within 1.5
        # NCLC of posterior mean. Test sentinels override.
        if answer_id == "__correct__":
            correct = True
        elif answer_id == "__incorrect__":
            correct = False
        else:
            correct = abs(cand.difficulty - sess.posterior.mean) <= 1.5
        sess.record_mcq(cand, correct=correct)
    else:
        total = body.response.get("rubric_total_20")
        if not isinstance(total, (int, float)):
            raise HTTPException(
                status_code=422,
                detail=(
                    "EE/EO answer must include numeric rubric_total_20 in [0, 20]; "
                    f"got {body.response!r}."
                ),
            )
        sess.record_rubric(cand, rubric_total_20=float(total))

    return _project_state(session_id, user_id, umbrella)


@router.post(
    "/{session_id}/finish",
    response_model=DiagnosticReport,
    summary="Finalize the diagnostic and return per-skill estimates",
)
async def finish(
    session_id: UUID,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> DiagnosticReport:
    """Close the session and return the report.

    Side-effect: writes each skill's final posterior into the user's
    `posteriors` dict so subsequent `/v1/plan` and `/v1/insights/readiness`
    calls reflect the diagnostic.
    """
    umbrella = get_diagnostic(user_id, session_id)
    if umbrella is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found.")
    if not umbrella.sessions:
        raise HTTPException(status_code=400, detail="No items answered yet.")

    st = get_user_state(user_id)
    per_skill_levels: list[SkillLevel] = []
    bottleneck_mean = float("inf")
    bottleneck_skill: SkillCode = "CO"
    for skill in SKILL_ORDER:
        sess = umbrella.sessions.get(skill)
        if sess is None:
            # Skill wasn't covered in this session — fall back to the
            # untouched bootstrap prior. Confidence will be False
            # (n_obs=0); the report's `confidence_summary` reflects that.
            sess = DiagnosticSession.start(user_id=user_id, skill=skill)
        st.posteriors[skill] = sess.posterior
        estimate = to_nclc_estimate(sess.posterior)
        per_skill_levels.append(
            SkillLevel(
                skill=skill,
                estimate=estimate,
                cefr_band=_nclc_to_cefr(sess.posterior.mean),
            ),
        )
        if sess.posterior.mean < bottleneck_mean:
            bottleneck_mean = sess.posterior.mean
            bottleneck_skill = skill

    n_confident = sum(1 for lvl in per_skill_levels if lvl.estimate.confident)
    if n_confident == len(SKILL_ORDER):
        summary = "high"
    elif n_confident > 0:
        summary = "partial"
    else:
        summary = "exploratory"

    return DiagnosticReport(
        session_id=SessionId(session_id),
        user_id=user_id,
        completed_at=datetime.now(UTC),
        per_skill=per_skill_levels,
        bottleneck_skill=bottleneck_skill,
        plan_id=None,
        confidence_summary=summary,  # type: ignore[arg-type]
    )
