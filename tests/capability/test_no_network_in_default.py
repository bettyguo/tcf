"""Capability tests: no network in default mode (`phase5_audit.md §9`, ADR-017).

The doctrine: under default configuration, **no path** through Phase 5's
runtime touches a remote host. The test enforces this at the syscall
layer by monkey-patching the stdlib `socket` API; any code path that
attempts a TCP connect or DNS lookup raises `BlockedNetworkError` and
the test fails with the offending function name.

Coverage:
- The audio pipeline (`run_audio_pipeline`) under stub backends.
- The `LocalWhisperBackend` construction (must not load weights or
  call the network at __init__).
- The `LocalMFAAligner` likewise.
- The `LocalXTTSBackend` likewise.
- The `score_ee` and `score_eo` worker stubs (Phase 5 local-only path).
- The end-to-end EO drill grade through the stub-backed pipeline.

The local *inference* paths (`LocalWhisperBackend.transcribe`,
`LocalMFAAligner.align`) **do** reach the filesystem to load model
weights when they exist — but they don't touch the network. Without
the weights available in CI, those paths raise `*BackendUnavailable*`
without a network call. We assert both: the failure mode is offline-
safe, and the success mode (via stubs) is offline-safe too.
"""

from __future__ import annotations

import pytest
from tcf_accel.errors import (
    ASRBackendUnavailableError,
    TTSBackendUnavailableError,
)
from tcf_accel_ml.alignment import LocalMFAAligner
from tcf_accel_ml.asr import LocalWhisperBackend
from tcf_accel_ml.tts import LocalXTTSBackend
from tcf_accel_sla.audio import run_audio_pipeline

from tests.capability._blocknet import BlockedNetworkError, block_network


def _good_audio() -> bytes:
    # 10 s of PCM16 mono @16k — clears the insufficient-data gate
    # downstream when fed through the stub pipeline.
    return b"\xff\xff" * (10 * 16_000)


# ─── Audio pipeline (stub backends) makes no network calls ─────


def test_audio_pipeline_under_stubs_makes_no_network_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under the stub backends (the test default for the pipeline),
    `run_audio_pipeline` completes without any socket egress."""
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")
    with block_network():
        outputs = run_audio_pipeline(_good_audio(), sample_rate_hz=16_000)
    # And the signal is well-formed (sanity).
    assert outputs.signal.signal_kind == "coarse_proxy"


def test_audio_pipeline_short_audio_no_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The insufficient-data path is also offline."""
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")
    with block_network():
        outputs = run_audio_pipeline(b"\xff\xff" * 100, sample_rate_hz=16_000)
    assert outputs.signal.display_label == "insufficient_data"


# ─── Local backends don't touch the network on construction ────


def test_local_whisper_backend_construct_is_offline() -> None:
    """`LocalWhisperBackend()` must not load weights / hit the network."""
    with block_network():
        backend = LocalWhisperBackend()
    assert backend.name == "local"


def test_local_mfa_aligner_construct_is_offline() -> None:
    with block_network():
        aligner = LocalMFAAligner()
    assert aligner.name == "local"


def test_local_xtts_backend_construct_is_offline() -> None:
    with block_network():
        backend = LocalXTTSBackend()
    assert backend.name == "local"


# ─── Local-backend failure modes are offline ──────────────────


def test_local_whisper_transcribe_failure_is_offline() -> None:
    """When `faster_whisper` is not installed, transcribe raises
    `ASRBackendUnavailableError` *without* a network call. The
    failure mode must remain offline-safe — even if the model couldn't
    be loaded, the code path doesn't reach for the network as a
    fallback."""
    with block_network(), pytest.raises(ASRBackendUnavailableError) as info:
        LocalWhisperBackend().transcribe(_good_audio(), sample_rate_hz=16_000)
    assert info.value.code == "E_ASR_001"


def test_local_mfa_align_failure_is_offline() -> None:
    """Without the `mfa` binary on PATH, the aligner raises offline."""
    with block_network(), pytest.raises(ASRBackendUnavailableError):
        LocalMFAAligner().align(_good_audio(), transcript="abc", sample_rate_hz=16_000)


def test_local_xtts_synthesize_failure_is_offline() -> None:
    """Without Coqui TTS installed, synthesize raises `TTSBackendUnavailableError`
    without making a network call."""
    with block_network(), pytest.raises(TTSBackendUnavailableError):
        LocalXTTSBackend().synthesize("Bonjour")


# ─── Worker stubs are offline ─────────────────────────────────


def test_score_ee_stub_makes_no_network_calls() -> None:
    """EE scoring (Phase 5 stub or Phase 7 calibrated) runs offline.

    The Phase 7 calibrated scorer (registered at worker-import time
    via `tcf_accel_ml.scoring.install_default_scorers()`) uses the
    deterministic `LLMCriticStub` by default — no network. Both the
    stub status (`"stub"`) and the calibrated status (`"graded"`)
    are acceptable; the load-bearing assertion is that no network
    call escaped during scoring.
    """
    from tcf_accel_worker.celery_app import celery_app  # noqa: PLC0415
    from tcf_accel_worker.tasks.score_ee import score_ee  # noqa: PLC0415

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    with block_network():
        result = score_ee.delay(
            {
                "text": "Le télétravail est important. Cependant, il isole.",
                "rubric_version": "ee.v1",
                "drill_kind": "ee_task",
                "task_number": 2,
                "target_word_count_range": [50, 200],
                "required_canadian_context": True,
            },
        ).get(timeout=1)
    assert result["phase7_status"] in {"stub", "graded"}


def test_score_eo_stub_makes_no_network_calls() -> None:
    """EO scoring runs offline.

    Same posture as the EE test: the calibrated scorer's LLM critic
    defaults to the deterministic local stub, so even with Phase 7
    installed the call makes no outbound network requests.
    """
    from tcf_accel_worker.celery_app import celery_app  # noqa: PLC0415
    from tcf_accel_worker.tasks.score_eo import score_eo  # noqa: PLC0415

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    with block_network():
        result = score_eo.delay(
            {
                "transcript": "bonjour le monde",
                "duration_s": 10.0,
                "target_duration_s": 12.0,
                "rubric_version": "eo.v1",
                "drill_kind": "eo_task",
                "task_number": 1,
            },
        ).get(timeout=1)
    assert result["phase7_status"] in {"stub", "graded"}


# ─── End-to-end: an EO drill grade is offline under stubs ─────


def test_eo_drill_grade_end_to_end_is_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The complete EO-drill flow (record → ASR → MFA → prosody → signal)
    completes without any socket egress under the stub backends."""
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")
    from datetime import UTC, datetime  # noqa: PLC0415
    from uuid import uuid4  # noqa: PLC0415

    from tcf_accel.schemas.common import Provenance  # noqa: PLC0415
    from tcf_accel.schemas.content import EOContent  # noqa: PLC0415
    from tcf_accel.schemas.item import Item  # noqa: PLC0415
    from tcf_accel_sla.drills import EOTaskDrill  # noqa: PLC0415

    item = Item(
        id=uuid4(),
        module="EO",
        cefr_level="B2",
        difficulty_irt=7.0,
        discrimination_irt=1.0,
        content=EOContent(
            task_number=1,
            examiner_prompts=["Présentez-vous."],
            candidate_prep_time_s=0,
            target_duration_s=180,
            rubric_version="eo.v1",
        ),
        provenance=Provenance(
            source="test",
            source_id="t",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
    )
    with block_network():
        result = EOTaskDrill().grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    assert result.pronunciation is not None
    assert result.pronunciation.signal_kind == "coarse_proxy"


# ─── Sanity: the fixture itself catches a real network attempt ────


def test_blocknet_actually_blocks_an_obvious_egress_attempt() -> None:
    """If the fixture ever stops working, this test would silently pass —
    so we keep one explicit assertion that a real outbound attempt raises."""
    import socket as _socket  # noqa: PLC0415

    with block_network(), pytest.raises(BlockedNetworkError):
        _socket.getaddrinfo("example.com", 80)
