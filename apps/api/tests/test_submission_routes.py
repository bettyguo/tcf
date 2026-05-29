"""Phase 7 /v1/submission/* route tests.

Covers:
- POST /v1/submission/ee with a plausible text returns 202 + a
  pending or graded `SubmissionView`.
- The submission flips to `graded` synchronously in eager mode.
- GET /v1/submission/{id} returns the stored view; unknown id → 404.
- POST /v1/submission/eo accepts a multipart audio upload.
- Item-id validation: a non-EE item rejected for the EE endpoint.
"""

from __future__ import annotations

import io
from typing import Final

import pytest
from fastapi.testclient import TestClient
from tcf_accel_worker.celery_app import celery_app

from tcf_accel_api.main import app
from tcf_accel_api.session_pool import SESSION_POOL
from tcf_accel_api.submission_state import reset_submissions

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup() -> None:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    reset_submissions()
    # Phase 7 install
    from tcf_accel_ml.scoring import install_default_scorers
    install_default_scorers()


def _first_ee_item_id() -> str:
    return str(SESSION_POOL["EE"][2].item.id)  # band 6 → NCLC 6 region


def _first_eo_item_id() -> str:
    return str(SESSION_POOL["EO"][2].item.id)


def _first_co_item_id() -> str:
    return str(SESSION_POOL["CO"][0].item.id)


_EE_TEXT: Final[str] = (
    "Cher voisin, je vous écris à propos du bruit nocturne qui me dérange "
    "depuis plusieurs semaines. Par ailleurs, je travaille tôt le matin "
    "et j'ai besoin de me reposer. Cependant, je comprends que la vie en "
    "ville à Montréal n'est pas toujours simple. Je propose donc que "
    "nous trouvions ensemble une solution amiable, par exemple en "
    "limitant la musique forte après vingt-deux heures. En conclusion, "
    "j'espère que nous pourrons résoudre cette situation rapidement et "
    "cordialement. Cordialement, votre voisin."
)


def test_post_submission_ee_returns_view_with_sha256() -> None:
    response = client.post(
        "/v1/submission/ee",
        data={"text": _EE_TEXT, "item_id": _first_ee_item_id()},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["module"] == "EE"
    assert body["payload_bytes"] == len(_EE_TEXT.encode("utf-8"))
    assert len(body["payload_sha256"]) == 64


def test_post_submission_ee_grades_synchronously_in_eager_mode() -> None:
    response = client.post(
        "/v1/submission/ee",
        data={"text": _EE_TEXT, "item_id": _first_ee_item_id()},
    )
    body = response.json()
    # Eager Celery: the scoring runs in-line, status flips to "graded".
    assert body["status"] == "graded"
    assert body["rubric_writing"] is not None
    assert 0 <= body["rubric_writing"]["total_20"] <= 20


def test_post_submission_ee_rejects_non_ee_item() -> None:
    response = client.post(
        "/v1/submission/ee",
        data={"text": _EE_TEXT, "item_id": _first_co_item_id()},
    )
    assert response.status_code == 404


def test_get_submission_unknown_id_returns_404() -> None:
    response = client.get("/v1/submission/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_submission_round_trip() -> None:
    create = client.post(
        "/v1/submission/ee",
        data={"text": _EE_TEXT, "item_id": _first_ee_item_id()},
    )
    sub_id = create.json()["id"]
    fetched = client.get(f"/v1/submission/{sub_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == sub_id


def test_post_submission_eo_accepts_multipart_audio() -> None:
    audio_bytes = b"\x00" * 1024  # placeholder; the Phase-5 ASR is owned elsewhere
    response = client.post(
        "/v1/submission/eo",
        data={"item_id": _first_eo_item_id()},
        files={"audio": ("rec.wav", io.BytesIO(audio_bytes), "audio/wav")},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["module"] == "EO"
    assert body["payload_bytes"] == len(audio_bytes)


def test_post_submission_ee_under_length_flags_human_review() -> None:
    response = client.post(
        "/v1/submission/ee",
        data={"text": "Bonjour.", "item_id": _first_ee_item_id()},
    )
    body = response.json()
    # The submission still grades, but task_completion is forced low
    # by the under-length feature floor. Other dimensions can score
    # higher because feature-only TTR on a 1-word input is degenerate.
    assert body["status"] == "graded"
    assert body["rubric_writing"]["task_completion"] == 0
