"""`/v1/mock-exam/*` — Phase 6 2h47 mock-exam orchestration.

Routes (`phase6_design.md §10`):

| Method | Path                                | Behavior                                  |
|--------|-------------------------------------|-------------------------------------------|
| POST   | `/v1/mock-exam/start`               | enforce cadence; build mock; return state |
| GET    | `/v1/mock-exam/{id}/state`          | current state (NEVER reveals answers)     |
| POST   | `/v1/mock-exam/{id}/advance`        | apply `advance` transition (Phase 6)      |
| GET    | `/v1/mock-exam/{id}/items/{module}` | redacted module items                     |
| POST   | `/v1/mock-exam/{id}/answer`         | record MCQ or rubric outcome              |
| POST   | `/v1/mock-exam/{id}/co-play`        | record a CO play (server-tracked)         |
| POST   | `/v1/mock-exam/{id}/tab-blur`       | report a tab-blur; forfeit if > 5 s       |
| POST   | `/v1/mock-exam/{id}/submit`         | finalize → enqueue score_mock             |
| GET    | `/v1/mock-exam/{id}/report`         | return the scored report                  |

All Item content is passed through `redact_item_dump` before leaving
the API boundary — the no-leak audit (`tests/test_mock_exam_no_leak.py`)
asserts the response body never contains `correct_option_id`,
`explanation`, or `answer_key`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from tcf_accel.errors import (
    MockCadenceExceededError,
    MockCoSinglePlayViolation,
    MockForfeitedError,
    MockInvalidTransitionError,
    MockNotScoredError,
)
from tcf_accel.ids import ItemId, MockExamId, UserId
from tcf_accel.schemas.api.mock_exam import (
    MockExamAnswer,
    MockExamCoPlay,
    MockExamReport,
    MockExamStart,
    MockExamState,
    MockExamTabBlur,
    PerModuleScore,
)
from tcf_accel.schemas.item import Module
from tcf_accel.schemas.scoring import NCLCEstimate
from tcf_accel_sla.estimator.nclc import to_nclc_estimate
from tcf_accel_sla.mock_exam import (
    EXAM_SHAPE,
    MODULE_DURATION_S,
    MODULE_ORDER,
    BREAK_AFTER,
    BREAK_DURATION_S,
    CANONICAL_TAB_BLUR_GRACE_S,
    ItemOutcome,
    MockState,
    PooledMockItem,
    RubricOutcome,
    SelectorInputs,
    can_start_canonical,
    can_start_training,
    next_module,
    select_full_mock,
    transition,
)
from tcf_accel_sla.mock_exam.scorer import score_mock as score_mock_pure
from tcf_accel_sla.mock_exam.state import (
    InvalidMockTransitionError,
    is_terminal,
)
from tcf_accel_sla.session.exam_shape_floor import iso_week

from tcf_accel_api.mock_exam_pool import (
    find_pooled_mock,
    mock_bank,
    redact_item_dump,
)
from tcf_accel_api.mock_exam_state import (
    MockExam,
    get_mock,
    get_mock_store,
    history,
    journal,
    put_mock,
)
from tcf_accel_api.state import current_user_id, get_user_state

router = APIRouter(prefix="/v1/mock-exam", tags=["mock-exam"])

_OWNER_PHASE = 6


# ─── projections ─────────────────────────────────────────────────


def _wire_status(state: MockState) -> str:
    if state == MockState.SCORED:
        return "scored"
    if state == MockState.FINISHED:
        return "submitted"
    return "in_progress"


def _seconds_remaining(mock: MockExam, now: datetime) -> int | None:
    """Soft countdown the UI uses; server is the source of truth for locking."""
    if mock.current_module is None or mock.module_started_at is None:
        return None
    target = MODULE_DURATION_S.get(mock.current_module, 0)
    elapsed = (now - mock.module_started_at).total_seconds()
    return max(0, int(target - elapsed))


def _project_state(mock: MockExam, *, now: datetime | None = None) -> MockExamState:
    now = now or datetime.now(UTC)
    return MockExamState(
        id=mock.id,
        user_id=mock.user_id,
        mode=mock.mode,
        status=_wire_status(mock.state),
        started_at=mock.started_at,
        finished_at=mock.finished_at,
        current_module=mock.current_module,
        current_item_id=None,  # the player tracks its own cursor
        seconds_remaining_in_module=_seconds_remaining(mock, now),
    )


def _raise_forfeited(mock: MockExam) -> None:
    if mock.state == MockState.FORFEITED:
        err = MockForfeitedError(mock_id=str(mock.id))
        raise HTTPException(
            status_code=err.http_status, detail=err.to_envelope(),
        )


def _require_mock(user_id: UserId, mock_id: UUID) -> MockExam:
    mock = get_mock(user_id, mock_id)
    if mock is None:
        raise HTTPException(status_code=404, detail=f"Mock exam {mock_id} not found.")
    return mock


def _apply_transition(
    mock: MockExam,
    event: str,
    *,
    now: datetime,
    reason: str,
) -> None:
    """Apply a state-machine transition or raise the canonical 409."""
    try:
        next_state = transition(mock.state, event, mode=mock.mode)  # type: ignore[arg-type]
    except InvalidMockTransitionError as exc:
        err = MockInvalidTransitionError(
            from_state=mock.state.value,
            event=event,
            detail=str(exc),
        )
        raise HTTPException(
            status_code=err.http_status, detail=err.to_envelope(),
        ) from exc
    journal(mock, at=now, to_state=next_state, reason=reason)


# ─── routes ──────────────────────────────────────────────────────


@router.post(
    "/start",
    response_model=MockExamState,
    status_code=201,
    summary="Start a full mock exam (Phase 6 owner)",
)
async def start(
    body: MockExamStart,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> MockExamState:
    """Create a new mock-exam session.

    Enforces ADR-033 cadence cap. `mode=canonical` is the default
    and the only mode that updates the NCLC posterior.
    """
    now = datetime.now(UTC)
    store = get_mock_store(user_id)
    hist = list(history(user_id))

    if body.mode == "canonical":
        ok, reason = can_start_canonical(
            hist, now=now, first_mock_at=store.first_canonical_at,
        )
    else:
        ok, reason = can_start_training(hist, now=now)

    if not ok and not body.force:
        err = MockCadenceExceededError(reason=reason)
        raise HTTPException(
            status_code=err.http_status, detail=err.to_envelope(),
        )

    mock_id = MockExamId(uuid4())
    bank = mock_bank()
    inputs = SelectorInputs(
        user_id=user_id,
        iso_week=iso_week(now),
        bank=bank,
        seen_within_30d=frozenset(),
        seen_ever=frozenset(),
    )
    selection = select_full_mock(inputs)

    items_by_module: dict[Module, list[PooledMockItem]] = {
        module: result.items for module, result in selection.items()
    }
    warnings = [
        w
        for r in selection.values()
        for w in r.warnings
    ]
    mock = MockExam(
        id=mock_id,
        user_id=user_id,
        mode=body.mode,
        state=MockState.SCHEDULED,
        started_at=now,
        items_by_module=items_by_module,
        current_module=None,
        seconds_remaining_in_module=0,
        state_entered_at=now,
        selector_warnings=warnings,
    )
    _apply_transition(mock, "start", now=now, reason="start")
    put_mock(user_id, mock)
    return _project_state(mock, now=now)


@router.get(
    "/{exam_id}/state",
    response_model=MockExamState,
    summary="Current mock-exam state (never reveals answers)",
)
async def get_state(
    exam_id: MockExamId,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> MockExamState:
    """Return the current state envelope — no answer fields, ever."""
    mock = _require_mock(user_id, exam_id)
    return _project_state(mock)


@router.post(
    "/{exam_id}/advance",
    response_model=MockExamState,
    summary="Advance through the exam state machine (Phase 6 additive)",
)
async def advance(
    exam_id: MockExamId,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> MockExamState:
    """Advance to the next state.

    Used by the player when the module timer expires or the learner
    submits a module early. The break clocks also advance via this
    endpoint.
    """
    mock = _require_mock(user_id, exam_id)
    _raise_forfeited(mock)
    now = datetime.now(UTC)
    _apply_transition(mock, "advance", now=now, reason="advance")

    if mock.state in {
        MockState.CO_ACTIVE,
        MockState.CE_ACTIVE,
        MockState.EE_ACTIVE,
        MockState.EO_ACTIVE,
    }:
        # Just entered a module — set the timer.
        mod = next_module(_prev_break_for(mock.state)) or _module_of_active(
            mock.state,
        )
        mock.current_module = mod
        mock.module_started_at = now
    elif mock.state in {
        MockState.BREAK_1,
        MockState.BREAK_2,
        MockState.BREAK_3,
    }:
        mock.current_module = None

    return _project_state(mock, now=now)


def _module_of_active(state: MockState) -> Module:
    mapping = {
        MockState.CO_ACTIVE: "CO",
        MockState.CE_ACTIVE: "CE",
        MockState.EE_ACTIVE: "EE",
        MockState.EO_ACTIVE: "EO",
    }
    return mapping[state]


def _prev_break_for(state: MockState) -> MockState:
    """Return the BREAK_n that precedes `state`; STARTED for CO_ACTIVE."""
    mapping = {
        MockState.CO_ACTIVE: MockState.STARTED,
        MockState.CE_ACTIVE: MockState.BREAK_1,
        MockState.EE_ACTIVE: MockState.BREAK_2,
        MockState.EO_ACTIVE: MockState.BREAK_3,
    }
    return mapping[state]


@router.get(
    "/{exam_id}/items/{module}",
    summary="Module items (redacted; answer keys never included)",
)
async def get_items(
    exam_id: MockExamId,
    module: Module,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> list[dict[str, Any]]:
    """Return the redacted items for one module.

    The response is a list of dicts (not typed `Item`) because the
    redaction layer strips fields that the frozen `Item` model requires
    — see `phase6_design.md §10.1`.
    """
    mock = _require_mock(user_id, exam_id)
    _raise_forfeited(mock)
    pool = mock.items_by_module.get(module, [])
    out: list[dict[str, Any]] = []
    for p in pool:
        dump = redact_item_dump(p.item)
        # Surface the IRT fields and CEFR at top-level — the candidate
        # & UI need them and they aren't answer keys.
        dump["difficulty_irt"] = p.difficulty
        dump["discrimination_irt"] = p.discrimination
        dump["cefr_level"] = p.cefr
        if p.task_number is not None:
            dump["task_number"] = p.task_number
        out.append(dump)
    return out


@router.post(
    "/{exam_id}/answer",
    response_model=MockExamState,
    summary="Record an MCQ or rubric outcome",
)
async def answer(
    exam_id: MockExamId,
    body: MockExamAnswer,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> MockExamState:
    """Record one item's outcome.

    The server owns the correct-answer key — the client sends only the
    selected option id; correctness is derived here so a tampered
    client cannot inflate the score.
    """
    mock = _require_mock(user_id, exam_id)
    _raise_forfeited(mock)
    pooled = find_pooled_mock(UUID(str(body.item_id)))
    if pooled is None:
        raise HTTPException(status_code=404, detail=f"Item {body.item_id} not found.")

    if body.kind == "mcq":
        if body.selected_option_id is None:
            raise HTTPException(
                status_code=422,
                detail="kind=mcq requires selected_option_id.",
            )
        # The server-owned correct key:
        questions = pooled.item.content.questions  # type: ignore[union-attr]
        correct_option_id = questions[0].correct_option_id
        outcome = ItemOutcome(
            item_id=ItemId(pooled.item.id),
            module=body.module,
            difficulty=pooled.difficulty,
            discrimination=pooled.discrimination,
            correct=(body.selected_option_id == correct_option_id),
            rt_ms=body.rt_ms,
        )
        mock.outcomes[pooled.item.id] = outcome
    else:  # rubric
        if body.rubric_total_20 is None or body.task_number is None:
            raise HTTPException(
                status_code=422,
                detail="kind=rubric requires rubric_total_20 and task_number.",
            )
        outcome_r = RubricOutcome(
            item_id=ItemId(pooled.item.id),
            module=body.module,
            task_number=body.task_number,
            prompt_target_nclc=pooled.difficulty,
            rubric_total_20=body.rubric_total_20,
        )
        mock.outcomes[pooled.item.id] = outcome_r

    return _project_state(mock)


@router.post(
    "/{exam_id}/co-play",
    response_model=MockExamState,
    summary="Record a CO audio play (single play enforced server-side)",
)
async def co_play(
    exam_id: MockExamId,
    body: MockExamCoPlay,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> MockExamState:
    """Increment the play count for a CO item; refuse if already played.

    ADR-029 + `phase6_think.md §2.3`: each CO audio plays exactly once
    per mock. The server tracks the count; the client cannot re-trigger.
    """
    mock = _require_mock(user_id, exam_id)
    _raise_forfeited(mock)
    item_uuid = UUID(str(body.item_id))
    if mock.co_plays.get(ItemId(item_uuid), 0) >= 1:
        err = MockCoSinglePlayViolation(item_id=str(body.item_id))
        raise HTTPException(
            status_code=err.http_status, detail=err.to_envelope(),
        )
    mock.co_plays[ItemId(item_uuid)] = 1
    return _project_state(mock)


@router.post(
    "/{exam_id}/tab-blur",
    response_model=MockExamState,
    summary="Report a tab-blur event; canonical forfeits past the grace window",
)
async def tab_blur(
    exam_id: MockExamId,
    body: MockExamTabBlur,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> MockExamState:
    """Apply the canonical-mode forfeit rule.

    `phase6_design.md §10.3` + ADR-032: in canonical mode, a tab-blur
    longer than `CANONICAL_TAB_BLUR_GRACE_S` forfeits the mock. Training
    mode no-ops.
    """
    mock = _require_mock(user_id, exam_id)
    if is_terminal(mock.state):
        return _project_state(mock)
    if mock.mode == "canonical" and body.duration_ms > CANONICAL_TAB_BLUR_GRACE_S * 1000:
        now = datetime.now(UTC)
        _apply_transition(
            mock,
            "tab_blur_exceeded",
            now=now,
            reason=f"tab_blur_{body.duration_ms}ms",
        )
    return _project_state(mock)


@router.post(
    "/{exam_id}/submit",
    response_model=MockExamState,
    summary="Submit the mock for scoring",
)
async def submit(
    exam_id: MockExamId,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> MockExamState:
    """Move to FINISHED, enqueue the scoring task, then SCORED.

    Training mode mocks are scored but do *not* update the user's
    canonical mock streak; the report renderer flags this.
    """
    mock = _require_mock(user_id, exam_id)
    _raise_forfeited(mock)
    now = datetime.now(UTC)

    if mock.state == MockState.EO_ACTIVE:
        _apply_transition(mock, "submit_final", now=now, reason="submit_final")
    elif mock.state != MockState.FINISHED:
        # Permit submit from EO_DONE / EO_ACTIVE only.
        if mock.state == MockState.EO_DONE:
            _apply_transition(
                mock, "submit_final", now=now, reason="submit_final",
            )
        else:
            err = MockInvalidTransitionError(
                from_state=mock.state.value,
                event="submit_final",
                detail="submit only valid from EO_ACTIVE or EO_DONE",
            )
            raise HTTPException(
                status_code=err.http_status, detail=err.to_envelope(),
            )

    mock.finished_at = now

    # Score synchronously by calling the pure scorer. The celery
    # `score_mock` task wraps the same callable and is the deferred
    # path used in production; here we call it inline so the API
    # remains independent of the worker package (clean dependency
    # graph: api → sla → shared).
    drill_state = get_user_state(user_id)
    result = _score_inline(mock, drill_state)
    _apply_scored_result(mock, result, drill_state)
    _apply_transition(mock, "score_complete", now=now, reason="scored")
    mock.scored_at = now
    return _project_state(mock, now=now)


def _score_inline(mock: MockExam, drill_state: Any) -> dict[str, Any]:
    co = [o for o in mock.outcomes.values() if isinstance(o, ItemOutcome) and o.module == "CO"]
    ce = [o for o in mock.outcomes.values() if isinstance(o, ItemOutcome) and o.module == "CE"]
    ee = [o for o in mock.outcomes.values() if isinstance(o, RubricOutcome) and o.module == "EE"]
    eo = [o for o in mock.outcomes.values() if isinstance(o, RubricOutcome) and o.module == "EO"]
    drill_posteriors = {s: p for s, p in drill_state.posteriors.items()}
    scored = score_mock_pure(
        co=co, ce=ce, ee=ee, eo=eo, drill_posteriors=drill_posteriors,
    )
    return {
        "mock_id": str(mock.id),
        "per_skill": {
            s: {
                "skill": score.skill,
                "raw": score.raw,
                "max_raw": score.max_raw,
                "n_items": score.n_items,
                "posterior": {
                    "skill": score.posterior.skill,
                    "mean": score.posterior.mean,
                    "variance": score.posterior.variance,
                    "n_obs": score.posterior.n_obs,
                    "difficulty_bands_seen": sorted(
                        score.posterior.difficulty_bands_seen,
                    ),
                },
                "divergence_alert": score.divergence_alert,
            }
            for s, score in scored.per_skill.items()
        },
        "overall_nclc": scored.overall_nclc,
        "overall_confident": scored.overall_confident,
        "bottleneck_skill": scored.bottleneck_skill,
        "divergence_alerts": scored.divergence_alerts,
    }


def _apply_scored_result(
    mock: MockExam,
    result: dict[str, Any],
    drill_state: Any,
) -> None:
    from tcf_accel_sla.estimator.nclc import SkillPosterior
    from tcf_accel_sla.mock_exam.scorer import MockSkillScore

    skill_scores: dict[str, MockSkillScore] = {}
    for skill, payload in result["per_skill"].items():
        post_payload = payload["posterior"]
        posterior = SkillPosterior(
            skill=skill,  # type: ignore[arg-type]
            mean=post_payload["mean"],
            variance=post_payload["variance"],
            n_obs=post_payload["n_obs"],
            difficulty_bands_seen=frozenset(post_payload["difficulty_bands_seen"]),
        )
        skill_scores[skill] = MockSkillScore(
            skill=skill,  # type: ignore[arg-type]
            raw=payload["raw"],
            max_raw=payload["max_raw"],
            n_items=payload["n_items"],
            posterior=posterior,
            divergence_alert=payload.get("divergence_alert"),
        )
    mock.skill_scores = skill_scores
    mock.overall_nclc = result["overall_nclc"]
    mock.overall_confident = result["overall_confident"]
    mock.bottleneck_skill = result["bottleneck_skill"]
    mock.divergence_alerts = list(result.get("divergence_alerts", []))

    # Canonical-mock streak bookkeeping (Phase 4 readiness gate).
    if mock.mode == "canonical":
        # A "green-eligible" mock is one where every per-skill posterior
        # is confident *and* the composite is at or above the target.
        all_confident = mock.overall_confident
        target = getattr(drill_state, "target_nclc", 7)
        composite = mock.overall_nclc or 0
        if all_confident and composite >= target:
            drill_state.canonical_mock_streak_green += 1
        else:
            drill_state.canonical_mock_streak_green = 0


@router.get(
    "/{exam_id}/report",
    response_model=MockExamReport,
    summary="Fetch the scored mock-exam report",
)
async def get_report(
    exam_id: MockExamId,
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> MockExamReport:
    """Return the headline report.

    The full Markdown/HTML report lives at `item_log_uri`; the wire
    response is intentionally compact (see `phase6_design.md §7`).
    """
    mock = _require_mock(user_id, exam_id)
    if mock.state != MockState.SCORED or mock.skill_scores is None:
        err = MockNotScoredError(state=mock.state.value)
        raise HTTPException(
            status_code=err.http_status, detail=err.to_envelope(),
        )

    per_module: list[PerModuleScore] = []
    for skill in MODULE_ORDER:
        score = mock.skill_scores[skill]  # type: ignore[index]
        estimate = NCLCEstimate(
            skill=skill,
            posterior_mean=score.posterior.mean,
            ci_low=score.posterior.ci_low,
            ci_high=score.posterior.ci_high,
            confident=score.posterior.confident,
            n_observations=score.posterior.n_obs,
        )
        per_module.append(
            PerModuleScore(
                module=skill,
                raw_score=score.raw,
                max_score=score.max_raw,
                estimate=estimate,
            ),
        )

    # The wire schema requires an integer overall_nclc. When the
    # estimator is not confident we still return the floor of the
    # bottleneck mean for shape compatibility — `overall_confident=False`
    # is the UI gate to suppress the display (master prompt §6.2).
    overall = mock.overall_nclc if mock.overall_nclc is not None else max(
        1,
        min(
            12,
            int(
                min(s.posterior.mean for s in mock.skill_scores.values()),  # type: ignore[union-attr]
            ),
        ),
    )
    bottleneck = mock.bottleneck_skill or "EE"

    return MockExamReport(
        id=mock.id,
        user_id=mock.user_id,
        completed_at=mock.scored_at or mock.finished_at or mock.started_at,
        per_module=per_module,
        overall_nclc=overall,
        overall_confident=mock.overall_confident,
        bottleneck_skill=bottleneck,
        item_log_uri=f"local://mock_log/{mock.id}.jsonl",
    )


__all__ = ["router"]
