"""Prosody analyzers (`phase5_design.md §5.1`).

Three signals feed `PronunciationProsody`:

- `speech_rate_wpm` — words per minute, from the ASR transcript.
- `pause_count` + `mean_pause_ms` — silences ≥ 200 ms inside the
  utterance, from the MFA alignment timestamps.
- `pitch_range_hz` — f0 max minus f0 min, computed by `librosa` over
  the audio. The librosa import is lazy; in the absence of librosa,
  the analyzer returns `0.0` and the insufficient-data gate downstream
  treats it accordingly (Phase 7 may refine).

`analyze_prosody` is the single public entry point: it takes the audio
+ ASR result + alignments and returns a `PronunciationProsody`. All
inputs are dataclass-shaped, so tests using the stub backends don't
need any model weights.
"""

from __future__ import annotations

from tcf_accel_ml.prosody.analyze import analyze_prosody, speech_rate_wpm
from tcf_accel_ml.prosody.pause import detect_pauses, summarize_pauses
from tcf_accel_ml.prosody.pitch import pitch_range_hz

__all__ = [
    "analyze_prosody",
    "detect_pauses",
    "pitch_range_hz",
    "speech_rate_wpm",
    "summarize_pauses",
]
