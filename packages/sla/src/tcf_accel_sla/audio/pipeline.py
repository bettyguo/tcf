"""`run_audio_pipeline` — ASR → MFA → prosody → `PronunciationSignal`.

The single seam EO drills use to convert a recording into a typed
pronunciation signal. All `tcf_accel_ml` imports are **lazy**: the SLA
package stays importable without faster-whisper / librosa / mfa
installed (the test stubs work in any environment).

The backends default to whatever the env-var dispatch returns
(`get_asr_backend()` / `get_mfa_aligner()`), so tests just set
`TCF_ACCEL_ASR_BACKEND=stub` + `TCF_ACCEL_MFA_BACKEND=stub` to get a
deterministic pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for type checkers; runtime is lazy.
    from tcf_accel.schemas.pronunciation import PronunciationProsody, PronunciationSignal
    from tcf_accel_ml.alignment.mfa import MFAAligner, PhonemeAlignment
    from tcf_accel_ml.asr.backend import ASRBackend, ASRResult


@dataclass(frozen=True)
class AudioPipelineOutputs:
    """Bundle of pipeline outputs handed to the EO drill `grade()`."""

    asr: ASRResult
    alignments: list[PhonemeAlignment]
    prosody: PronunciationProsody
    signal: PronunciationSignal


def run_audio_pipeline(
    audio: bytes,
    *,
    sample_rate_hz: int,
    asr_backend: ASRBackend | None = None,
    mfa_aligner: MFAAligner | None = None,
) -> AudioPipelineOutputs:
    r"""Run ASR → MFA → prosody → `build_signal` end-to-end.

    Lazy-imports the `tcf_accel_ml` modules so the SLA package stays
    importable in environments without faster-whisper / librosa / mfa.
    Tests pin behavior with the stub backends via the
    `TCF_ACCEL_{ASR,MFA}_BACKEND=stub` env vars or by passing
    backends/aligners directly.

    Example (test stub configuration):
        >>> import os
        >>> os.environ["TCF_ACCEL_ASR_BACKEND"] = "stub"
        >>> os.environ["TCF_ACCEL_MFA_BACKEND"] = "stub"
        >>> outputs = run_audio_pipeline(b"\\xff" * 32_000, sample_rate_hz=16_000)
        >>> outputs.signal.signal_kind
        'coarse_proxy'
        >>> del os.environ["TCF_ACCEL_ASR_BACKEND"]
        >>> del os.environ["TCF_ACCEL_MFA_BACKEND"]
    """
    # Lazy imports — keeps `packages/sla` clean in venvs without ml deps.
    from tcf_accel_ml.alignment import get_mfa_aligner  # noqa: PLC0415
    from tcf_accel_ml.asr import get_asr_backend  # noqa: PLC0415
    from tcf_accel_ml.pronunciation import build_signal  # noqa: PLC0415
    from tcf_accel_ml.prosody import analyze_prosody  # noqa: PLC0415

    backend = asr_backend if asr_backend is not None else get_asr_backend()
    aligner = mfa_aligner if mfa_aligner is not None else get_mfa_aligner()

    asr = backend.transcribe(audio, sample_rate_hz=sample_rate_hz)
    alignments = aligner.align(
        audio,
        transcript=asr.transcript,
        sample_rate_hz=sample_rate_hz,
    )
    prosody = analyze_prosody(
        audio=audio,
        sample_rate_hz=sample_rate_hz,
        asr=asr,
        alignments=alignments,
    )
    signal = build_signal(asr=asr, alignments=alignments, prosody=prosody)
    return AudioPipelineOutputs(
        asr=asr,
        alignments=alignments,
        prosody=prosody,
        signal=signal,
    )


__all__ = ["AudioPipelineOutputs", "run_audio_pipeline"]
