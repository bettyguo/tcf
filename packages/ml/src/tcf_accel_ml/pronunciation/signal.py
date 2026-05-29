"""`PronunciationSignal` factory (`phase5_design.md §5.2`, ADR-031).

`build_signal` is the **sanctioned** construction site for a
`PronunciationSignal` outside tests. The structural-lint rule
(`tests/lint/test_no_raw_pron_score_outside_allowlist.py`) blocks any
direct `.score` access on a `PronunciationSignal` instance from
application/UI code; the UI consumes `display_label` instead.

The factory takes the pipeline's three outputs (ASR result, alignment,
prosody) plus a reference phoneme sequence, computes PER, runs the
insufficient-data gate, and emits the signal. The `score` field is the
continuous [0, 1] complement of the PER (clipped); the planner reads
it, the UI does not.

`reference_phonemes(transcript)` produces a stub-friendly reference:
in production it would consult the LeFFF / Lexique-3 pronunciation
dictionary (deferred to §17 step 14); for the stub-backed Phase 5
pipeline it returns the source-text characters so PER is well-defined
end-to-end without external lookups.
"""

from __future__ import annotations

from typing import Final

from tcf_accel.schemas.pronunciation import PronunciationProsody, PronunciationSignal

from tcf_accel_ml.alignment.mfa import PhonemeAlignment
from tcf_accel_ml.asr.backend import ASRResult
from tcf_accel_ml.pronunciation.insufficient_data import display_label_from
from tcf_accel_ml.pronunciation.per import phoneme_error_rate

# The on-disk disclaimer copy is keyed by this version string
# (`packages/content/data/pron_disclaimers.{en,fr}.yaml` — landing
# with the EE/EO drills). Bumping this version invalidates the
# rendered disclaimer cache.
DISCLAIMER_VERSION: Final[str] = "v1.0"


def reference_phonemes(transcript: str) -> list[str]:
    """Stub-friendly reference phoneme sequence for a transcript.

    Production (deferred to §17 step 14): tokenize the transcript and
    look each word up in the LeFFF / Lexique 3.83 pronunciation
    dictionary; emit the concatenated IPA.

    Stub (Phase 5): return the non-whitespace characters of the
    transcript. The stub MFA aligner uses the same surrogate, so PER
    end-to-end is well-defined and `=0` when the learner reproduces
    the source text exactly.
    """
    return [c for c in transcript if not c.isspace()]


def _per_to_score(per: float) -> float:
    """Project PER ∈ [0, ∞) into a [0, 1] score. Saturating: PER ≥ 1 → 0."""
    return max(0.0, 1.0 - per)


def build_signal(
    *,
    asr: ASRResult,
    alignments: list[PhonemeAlignment],
    prosody: PronunciationProsody,
    reference: list[str] | None = None,
    disclaimer_version: str = DISCLAIMER_VERSION,
) -> PronunciationSignal:
    """Compose the pipeline outputs into a `PronunciationSignal`.

    The reference defaults to `reference_phonemes(asr.transcript)` when
    not supplied — that's the stub-friendly path. Production callers
    pass a dictionary-derived reference.

    The `display_label` is computed by the insufficient-data gate; the
    `score` is `1 - PER` (clipped). The factory is the only place that
    knows the relationship; callers consume the typed signal.

    Example:
        >>> from tcf_accel.schemas.pronunciation import PronunciationProsody
        >>> from tcf_accel_ml.asr.backend import ASRResult
        >>> asr = ASRResult(
        ...     transcript="bonjour le monde",
        ...     tokens=(), mean_confidence=0.9,
        ...     language="fr", duration_s=10.0,
        ... )
        >>> # 14 non-space chars; equal-length, identical phoneme stream → PER 0.
        >>> sig = build_signal(
        ...     asr=asr,
        ...     alignments=[],  # alignments don't affect PER here
        ...     prosody=PronunciationProsody(
        ...         pitch_range_hz=100.0, speech_rate_wpm=120.0,
        ...         pause_count=0, mean_pause_ms=0.0,
        ...     ),
        ...     reference=list("bonjourlemonde"),
        ... )
        >>> sig.display_label
        'strong'
        >>> sig.signal_kind
        'coarse_proxy'
    """
    ref = reference if reference is not None else reference_phonemes(asr.transcript)
    hyp = reference_phonemes(asr.transcript)
    per = phoneme_error_rate(ref, hyp)
    n_aligned = len(alignments) if alignments else len(hyp)
    label = display_label_from(
        per=per,
        asr_mean_confidence=asr.mean_confidence,
        duration_s=asr.duration_s,
        n_phonemes_aligned=n_aligned,
    )
    return PronunciationSignal(
        score=_per_to_score(per),
        disclaimer_version=disclaimer_version,
        display_label=label,
        per=per,
        asr_mean_confidence=asr.mean_confidence,
        n_phonemes_aligned=n_aligned,
        duration_s=asr.duration_s,
        prosody=prosody,
    )


__all__ = ["DISCLAIMER_VERSION", "build_signal", "reference_phonemes"]
