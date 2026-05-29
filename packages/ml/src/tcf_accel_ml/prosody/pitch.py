"""Pitch (f0) range via librosa.

The real implementation extracts f0 over the utterance with
`librosa.pyin` and returns `max(f0) - min(f0)`. `librosa` is a heavy
import (numpy + scipy + numba), so the call is **lazy**: the import is
deferred until `pitch_range_hz` is first called, and an `ImportError`
returns `0.0` rather than raising — pitch is one signal among many,
and the pronunciation pipeline tolerates its absence by routing the
overall signal to `display_label='insufficient_data'` via the gate.

A pure-stdlib heuristic substitutes when librosa is absent (the stub
path used in CI): we return a placeholder of `0.0` rather than guess a
range from waveform bytes — the contract is "honest zero," not a
plausible-looking lie.
"""

from __future__ import annotations


def pitch_range_hz(audio: bytes, *, sample_rate_hz: int) -> float:
    """Estimate f0 max - f0 min over the audio (Hz).

    Returns `0.0` if librosa is not installed or the analysis fails.
    The pronunciation pipeline reads the value and either uses it or
    routes the surfacing label to `insufficient_data` per the gate.
    """
    try:
        import librosa  # type: ignore[import-not-found]  # noqa: PLC0415
        import numpy as np  # type: ignore[import-not-found]  # noqa: PLC0415
    except ImportError:
        return 0.0

    if not audio or sample_rate_hz <= 0:
        return 0.0

    try:
        pcm = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        # PYIN: f0 in Hz; we use the typical voice range 65–500 Hz.
        f0, _voiced_flag, _voiced_prob = librosa.pyin(  # pragma: no cover - librosa runtime
            pcm,
            fmin=65.0,
            fmax=500.0,
            sr=sample_rate_hz,
        )
        voiced = f0[~np.isnan(f0)]
        if voiced.size == 0:
            return 0.0
        return float(voiced.max() - voiced.min())
    except Exception:
        return 0.0


__all__ = ["pitch_range_hz"]
