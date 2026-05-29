"""`SpeakingFeatures` extractor.

Inherits the writing feature extraction (computed on the transcript)
and adds speech-specific signals: WPM, pauses, fillers, pitch, and
the pronunciation-pipeline outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from tcf_accel.schemas.pronunciation import PronunciationSignal

from tcf_accel_ml.scoring.features.writing import WritingFeatures, extract_writing_features

#: Frequent French filler words. Phase 5's ASR transcribes these; we
#: count them after lowercase + simple tokenisation.
_FILLERS: Final[frozenset[str]] = frozenset({
    "euh", "euhm", "ben", "bah", "hein", "hmm", "voilà",
    "enfin", "tu sais", "tu vois", "comme",
})

#: Self-correction markers — overt repair phrases the learner uses to
#: restart a sentence. Frequent in B1–B2 spontaneous speech.
_SELF_CORRECTION_PHRASES: Final[tuple[str, ...]] = (
    "non pardon", "je veux dire", "enfin je veux dire",
    "ou plutôt", "non, plutôt", "non, je",
)


@dataclass(frozen=True)
class SpeakingFeatures:
    """Feature vector consumed by the EO rubric calibrator.

    Includes the writing features computed on the transcript (content
    dimensions) plus speech-specific signals.
    """

    writing: WritingFeatures
    duration_s: float
    wpm: float
    pause_count_per_minute: float
    pause_total_ratio: float
    filler_count_per_minute: float
    mean_pitch: float
    pitch_range: float
    phoneme_error_rate: float | None
    asr_mean_confidence: float
    self_correction_count: int
    pronunciation_display_label: str

    def as_vector(self) -> list[float]:
        """Stable feature order for the EO calibrator."""
        per = self.phoneme_error_rate if self.phoneme_error_rate is not None else -1.0
        return [
            *self.writing.as_vector(),
            self.duration_s,
            self.wpm,
            self.pause_count_per_minute,
            self.pause_total_ratio,
            self.filler_count_per_minute,
            self.mean_pitch,
            self.pitch_range,
            per,
            self.asr_mean_confidence,
            float(self.self_correction_count),
        ]


def _count_fillers(transcript: str) -> int:
    tokens = [t.strip(".,;:!?\"'()«»").casefold() for t in transcript.split()]
    return sum(1 for t in tokens if t in _FILLERS)


def _count_self_corrections(transcript: str) -> int:
    lower = transcript.casefold()
    return sum(lower.count(phrase) for phrase in _SELF_CORRECTION_PHRASES)


def _wpm(transcript: str, duration_s: float) -> float:
    if duration_s <= 0:
        return 0.0
    n_words = len(re.findall(r"[^\W\d_]+", transcript, re.UNICODE))
    return (n_words / duration_s) * 60.0


def extract_speaking_features(
    *,
    transcript: str,
    duration_s: float,
    asr_mean_confidence: float = 0.0,
    pronunciation_signal: PronunciationSignal | None = None,
    pause_count: int = 0,
    pause_total_s: float = 0.0,
) -> SpeakingFeatures:
    """Build a `SpeakingFeatures` from the pipeline outputs.

    `pronunciation_signal` is the Phase 5 output. When `None`, the
    pronunciation fields are filled with neutral defaults and the
    `pronunciation_display_label` is reported as `"insufficient_data"`.

    Example:
        >>> f = extract_speaking_features(
        ...     transcript="Bonjour le monde.",
        ...     duration_s=2.0,
        ...     asr_mean_confidence=0.9,
        ... )
        >>> f.duration_s
        2.0
        >>> 0.0 <= f.wpm
        True
        >>> f.pronunciation_display_label
        'insufficient_data'
    """
    writing = extract_writing_features(transcript)
    n_minutes = max(1e-9, duration_s / 60.0)
    fillers = _count_fillers(transcript)
    selfc = _count_self_corrections(transcript)

    if pronunciation_signal is not None:
        per: float | None = pronunciation_signal.per
        prosody = pronunciation_signal.prosody
        mean_pitch = prosody.pitch_range_hz  # we only have range; approximate mid
        pitch_range = prosody.pitch_range_hz
        label = pronunciation_signal.display_label
        if pause_count == 0 and prosody.pause_count:
            pause_count = prosody.pause_count
        if pause_total_s == 0.0 and prosody.pause_count and prosody.mean_pause_ms:
            pause_total_s = prosody.pause_count * (prosody.mean_pause_ms / 1000.0)
    else:
        per = None
        mean_pitch = 0.0
        pitch_range = 0.0
        label = "insufficient_data"

    pause_ratio = (pause_total_s / duration_s) if duration_s > 0 else 0.0

    return SpeakingFeatures(
        writing=writing,
        duration_s=duration_s,
        wpm=_wpm(transcript, duration_s),
        pause_count_per_minute=pause_count / n_minutes,
        pause_total_ratio=min(1.0, max(0.0, pause_ratio)),
        filler_count_per_minute=fillers / n_minutes,
        mean_pitch=mean_pitch,
        pitch_range=pitch_range,
        phoneme_error_rate=per,
        asr_mean_confidence=asr_mean_confidence,
        self_correction_count=selfc,
        pronunciation_display_label=label,
    )


__all__ = ["SpeakingFeatures", "extract_speaking_features"]
