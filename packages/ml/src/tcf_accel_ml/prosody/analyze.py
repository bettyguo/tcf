"""Prosody assembly — produces a `PronunciationProsody` from pipeline outputs.

Composes the three primitive analyses (pause, pitch, speech-rate) into
the schema-typed `PronunciationProsody` consumed by
`PronunciationSignal` (Phase 5 step 7). Pure logic — no model imports
here; the heavy lifting lives in `pitch.py` (lazy librosa) and
`pause.py` (alignment-based).
"""

from __future__ import annotations

from tcf_accel.schemas.pronunciation import PronunciationProsody

from tcf_accel_ml.alignment.mfa import PhonemeAlignment
from tcf_accel_ml.asr.backend import ASRResult
from tcf_accel_ml.prosody.pause import detect_pauses, summarize_pauses
from tcf_accel_ml.prosody.pitch import pitch_range_hz


def speech_rate_wpm(transcript: str, duration_s: float) -> float:
    """Words per minute from an ASR transcript + utterance duration.

    A zero or negative duration returns 0.0 (insufficient signal); the
    `PronunciationSignal` insufficient-data gate handles that path.

    Example:
        >>> speech_rate_wpm("bonjour le monde", 1.0)  # 3 words in 1 s
        180.0
        >>> speech_rate_wpm("", 1.0)
        0.0
        >>> speech_rate_wpm("a", 0.0)
        0.0

    Complexity: O(len(transcript)).
    """
    if duration_s <= 0.0:
        return 0.0
    n_words = len(transcript.split())
    return (n_words / duration_s) * 60.0


def analyze_prosody(
    *,
    audio: bytes,
    sample_rate_hz: int,
    asr: ASRResult,
    alignments: list[PhonemeAlignment],
) -> PronunciationProsody:
    """Build a `PronunciationProsody` from the pipeline outputs.

    The function never raises — every analyzer is best-effort and
    contributes whatever it can; the `PronunciationSignal` gate
    decides whether the aggregated quality is enough to surface a
    label (`phase5_design.md §5.3`).
    """
    pauses = detect_pauses(alignments)
    count, mean_ms = summarize_pauses(pauses)
    return PronunciationProsody(
        pitch_range_hz=pitch_range_hz(audio, sample_rate_hz=sample_rate_hz),
        speech_rate_wpm=speech_rate_wpm(asr.transcript, asr.duration_s),
        pause_count=count,
        mean_pause_ms=mean_ms,
    )


__all__ = ["analyze_prosody", "speech_rate_wpm"]
