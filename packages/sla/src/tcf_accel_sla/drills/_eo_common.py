"""EO drill common grading shell (`phase5_design.md §4.4`).

All EO drills (`eo_task`, `eo_picture`, `eo_spontaneous`, `eo_roleplay`,
`eo_repair`) share the same essential pipeline: decode the learner's
recording, run ASR → MFA → prosody → `PronunciationSignal`, and emit
a rubric-pending `Interaction` whose `pronunciation` field carries the
coarse-proxy signal (ADR-031).

The audio arrives in the response dict under the `audio` key. Tests
pass raw `bytes`; the API layer base64-decodes from the JSON wire
before calling `grade()` (the wire-decode lives in the route).

Drill-specific concerns (prep time, target duration, follow-up
prompts) are owned by the concrete drill subclasses; this module owns
only the shared pipeline → result projection.
"""

from __future__ import annotations

from typing import Any, Final

from tcf_accel_sla.audio import run_audio_pipeline
from tcf_accel_sla.drills.base import DrillResult

# When the recording is missing or empty we emit an insufficient-data
# stub — the drill's other signals (`response_present=False`) are the
# tell for the audit; the planner ignores the pronunciation score
# anyway via the gate.
EO_DEFAULT_SAMPLE_RATE_HZ: Final[int] = 16_000


def _extract_audio_bytes(response: dict[str, Any]) -> bytes:
    """Pull raw PCM bytes from the response, accepting either bytes or base64.

    Test callers pass `audio: bytes` directly; the API route decodes the
    JSON-encoded base64 *before* calling the drill so this function
    sees raw bytes in both paths.
    """
    audio = response.get("audio", b"")
    if isinstance(audio, bytes):
        return audio
    if isinstance(audio, (bytearray, memoryview)):
        return bytes(audio)
    # Conservative fallback: a non-bytes payload is treated as no audio.
    return b""


def grade_eo_recording(
    response: dict[str, Any],
    *,
    drill_kind: str,
    rubric_version: str,
    task_number: int | None = None,
) -> DrillResult:
    """Run the audio pipeline and build a rubric-pending `DrillResult`.

    The result carries:
    - `correct = None` (Phase 7 rubric fills this in).
    - `pronunciation = PronunciationSignal` from `run_audio_pipeline`.
    - `graded_score = {"pending": True, "phase7_status": "stub",
        "drill_origin", "rubric_version", "task_number", "transcript",
        "duration_s", "speech_rate_wpm"}` — the metadata Phase 7 will
        consume.
    - `raw_response = {"audio_bytes": len(audio), "transcript": ...,
        "duration_s": ...}` — bytes count, NOT the bytes (audio is
        never persisted by default; ADR-017).

    Missing or empty audio yields a `DrillResult` with `correct=False`
    and `graded_score.pending=False, phase7_status="no_audio"` so the
    learner sees a clear error rather than a silently-pending row.
    """
    audio = _extract_audio_bytes(response)
    sample_rate_hz = int(response.get("sample_rate_hz", EO_DEFAULT_SAMPLE_RATE_HZ))

    if not audio:
        return DrillResult(
            correct=False,
            partial_credit=0.0,
            raw_response={
                "audio_bytes": 0,
                "transcript": "",
                "duration_s": 0.0,
            },
            graded_score={
                "pending": False,
                "phase7_status": "no_audio",
                "drill_origin": drill_kind,
                "rubric_version": rubric_version,
                "task_number": task_number,
            },
        )

    outputs = run_audio_pipeline(audio, sample_rate_hz=sample_rate_hz)
    return DrillResult(
        correct=None,
        raw_response={
            "audio_bytes": len(audio),  # NB: never the bytes themselves (ADR-017)
            "transcript": outputs.asr.transcript,
            "duration_s": outputs.asr.duration_s,
        },
        pronunciation=outputs.signal,
        graded_score={
            "pending": True,
            "phase7_status": "stub",
            "drill_origin": drill_kind,
            "rubric_version": rubric_version,
            "task_number": task_number,
            "transcript": outputs.asr.transcript,
            "duration_s": outputs.asr.duration_s,
            "speech_rate_wpm": outputs.prosody.speech_rate_wpm,
            "pause_count": outputs.prosody.pause_count,
            "pronunciation_display_label": outputs.signal.display_label,
        },
    )


__all__ = ["EO_DEFAULT_SAMPLE_RATE_HZ", "grade_eo_recording"]
