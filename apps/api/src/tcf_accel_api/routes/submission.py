"""`/v1/submission/*` — async EE/EO grading (Phase 7).

The submission upload routes use `multipart/form-data` so the artifact
(text or audio bytes) is streamed straight to operator storage; the
artifact itself is never echoed in the JSON body.

Persistence is in-process for Phase 7 (`submission_state.py`); the
Postgres + S3 swap-in is deferred to the same step that swaps practice
sessions.

In `task_always_eager=True` test mode the Celery `score_ee` / `score_eo`
task runs synchronously inside `delay()`, so the submission flips to
`graded` before the POST returns. Production runs the task on a worker
and the client polls `GET /v1/submission/{id}`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from tcf_accel.errors import NotImplementedRouteError
from tcf_accel.ids import ItemId, SubmissionId, UserId
from tcf_accel.schemas.api.submission import SubmissionView
from tcf_accel.schemas.content.ee import EEContent
from tcf_accel.schemas.content.eo import EOContent
from tcf_accel.schemas.scoring import SpeakingRubric, WritingRubric

from tcf_accel_api.session_pool import find_pooled
from tcf_accel_api.state import current_user_id
from tcf_accel_api.submission_state import (
    SubmissionRecord,
    create_submission,
    get_submission,
    update_submission,
)

router = APIRouter(prefix="/v1/submission", tags=["submission"])

_OWNER_PHASE = 7


def _raise_404(submission_id: SubmissionId) -> None:
    err = NotImplementedRouteError(phase=_OWNER_PHASE, route=f"/v1/submission/{submission_id}")
    raise HTTPException(status_code=404, detail=err.to_envelope(phase=_OWNER_PHASE))


def _resolve_ee(item_id: ItemId) -> EEContent:
    pooled = find_pooled(item_id)
    if pooled is None or pooled.item.module != "EE":
        raise HTTPException(status_code=404, detail={"error": "item_not_found_or_not_ee"})
    content = pooled.item.content
    if not isinstance(content, EEContent):  # pragma: no cover — defensive
        raise HTTPException(status_code=400, detail={"error": "item_content_not_ee"})
    return content


def _resolve_eo(item_id: ItemId) -> EOContent:
    pooled = find_pooled(item_id)
    if pooled is None or pooled.item.module != "EO":
        raise HTTPException(status_code=404, detail={"error": "item_not_found_or_not_eo"})
    content = pooled.item.content
    if not isinstance(content, EOContent):  # pragma: no cover — defensive
        raise HTTPException(status_code=400, detail={"error": "item_content_not_eo"})
    return content


def _enqueue_ee_grading(rec: SubmissionRecord, content: EEContent) -> None:
    """Submit the EE scoring task. In eager mode the call returns
    synchronously and `rec` is updated in-place.
    """
    from tcf_accel_worker.celery_app import celery_app
    from tcf_accel_worker.tasks.score_ee import score_ee

    text = rec.artifact.decode("utf-8", errors="replace")
    payload: dict[str, Any] = {
        "text": text,
        "prompt": content.prompt,
        "task_number": int(content.task_number),
        "target_word_count_range": list(content.target_word_count_range),
        "required_canadian_context": content.required_canadian_context,
        "rubric_version": content.rubric_version,
        "drill_kind": "ee_task",
    }
    try:
        async_result = score_ee.delay(payload)
    except Exception as exc:  # pragma: no cover — broker absence
        rec.status = "failed"
        rec.graded_at = datetime.now(UTC)
        rec.graded_score = {"error": str(exc)}
        update_submission(rec)
        return

    if celery_app.conf.task_always_eager:
        try:
            graded = async_result.get(timeout=5)
        except Exception as exc:  # pragma: no cover
            rec.status = "failed"
            rec.graded_at = datetime.now(UTC)
            rec.graded_score = {"error": str(exc)}
            update_submission(rec)
            return
        _apply_ee_graded(rec, graded)


def _enqueue_eo_grading(rec: SubmissionRecord, content: EOContent) -> None:
    from tcf_accel_worker.celery_app import celery_app
    from tcf_accel_worker.tasks.score_eo import score_eo

    payload: dict[str, Any] = {
        "transcript": "",
        "prompt": " | ".join(content.examiner_prompts) if content.examiner_prompts else "",
        "task_number": int(content.task_number),
        "duration_s": float(content.target_duration_s),
        "target_duration_s": float(content.target_duration_s),
        "rubric_version": content.rubric_version,
        "drill_kind": "eo_task",
        "asr_mean_confidence": 0.0,
    }
    try:
        async_result = score_eo.delay(payload)
    except Exception as exc:  # pragma: no cover
        rec.status = "failed"
        rec.graded_at = datetime.now(UTC)
        rec.graded_score = {"error": str(exc)}
        update_submission(rec)
        return

    if celery_app.conf.task_always_eager:
        try:
            graded = async_result.get(timeout=5)
        except Exception as exc:  # pragma: no cover
            rec.status = "failed"
            rec.graded_at = datetime.now(UTC)
            rec.graded_score = {"error": str(exc)}
            update_submission(rec)
            return
        _apply_eo_graded(rec, graded)


def _apply_ee_graded(rec: SubmissionRecord, graded: dict[str, Any]) -> None:
    rec.graded_score = dict(graded)
    rubric_blob = graded.get("rubric")
    if isinstance(rubric_blob, dict):
        try:
            rec.rubric_writing = WritingRubric.model_validate(rubric_blob)
        except Exception:
            rec.rubric_writing = None
    if rec.rubric_writing is not None:
        rec.status = "graded"
        rec.graded_at = datetime.now(UTC)
    update_submission(rec)


def _apply_eo_graded(rec: SubmissionRecord, graded: dict[str, Any]) -> None:
    rec.graded_score = dict(graded)
    rubric_blob = graded.get("rubric")
    if isinstance(rubric_blob, dict):
        try:
            rec.rubric_speaking = SpeakingRubric.model_validate(rubric_blob)
        except Exception:
            rec.rubric_speaking = None
    if rec.rubric_speaking is not None:
        rec.status = "graded"
        rec.graded_at = datetime.now(UTC)
    update_submission(rec)


@router.post(
    "/ee",
    response_model=SubmissionView,
    status_code=202,
    summary="Submit a written response for async grading",
)
async def submit_ee(
    item_id: Annotated[ItemId, Form(...)],
    text: Annotated[str, Form(description="The candidate's written response (UTF-8).")],
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> SubmissionView:
    """Enqueue an EE submission for the Phase 7 writing scorer."""
    content = _resolve_ee(item_id)
    artifact = text.encode("utf-8")
    rec = create_submission(
        user_id=user_id, item_id=item_id, module="EE", artifact=artifact,
    )
    _enqueue_ee_grading(rec, content)
    return rec.to_view()


@router.post(
    "/eo",
    response_model=SubmissionView,
    status_code=202,
    summary="Submit a recorded response for async grading",
)
async def submit_eo(
    item_id: Annotated[ItemId, Form(...)],
    audio: Annotated[UploadFile, File(description="The candidate's recording (wav/ogg/m4a).")],
    user_id: Annotated[UserId, Depends(current_user_id)],
) -> SubmissionView:
    """Enqueue an EO submission for the Phase 7 speaking scorer."""
    content = _resolve_eo(item_id)
    raw = await audio.read()
    rec = create_submission(
        user_id=user_id, item_id=item_id, module="EO", artifact=raw,
    )
    _enqueue_eo_grading(rec, content)
    return rec.to_view()


@router.get(
    "/{submission_id}",
    response_model=SubmissionView,
    summary="Poll a submission's grading status",
)
async def get_submission_view(submission_id: SubmissionId) -> SubmissionView:
    """Return the submission's current status and (when graded) its rubric."""
    rec = get_submission(submission_id)
    if rec is None:
        _raise_404(submission_id)
        raise AssertionError("unreachable")
    return rec.to_view()
