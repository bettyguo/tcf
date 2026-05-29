"""Pronunciation signal assembly (`phase5_design.md §5`, ADR-031).

Composes the ASR transcript, MFA alignment, and prosody features into
a `PronunciationSignal` (the coarse-proxy contract). The factory
`build_signal` is the **only** sanctioned construction site outside
tests — the structural lint rule (`tests/lint/`) keeps the `.score`
field out of UI/application code.

The `display_label_from` gate is the refuse-to-predict path: short
utterances, low-confidence ASR, or missing reference data resolve to
`"insufficient_data"` and the planner ignores the row.
"""

from __future__ import annotations

from tcf_accel_ml.pronunciation.insufficient_data import (
    DISPLAY_LABEL_PER_FAIR,
    DISPLAY_LABEL_PER_STRONG,
    INSUFFICIENT_ASR_CONFIDENCE,
    INSUFFICIENT_DURATION_S,
    INSUFFICIENT_PHONEMES,
    display_label_from,
)
from tcf_accel_ml.pronunciation.per import phoneme_error_rate
from tcf_accel_ml.pronunciation.signal import (
    DISCLAIMER_VERSION,
    build_signal,
    reference_phonemes,
)

__all__ = [
    "DISCLAIMER_VERSION",
    "DISPLAY_LABEL_PER_FAIR",
    "DISPLAY_LABEL_PER_STRONG",
    "INSUFFICIENT_ASR_CONFIDENCE",
    "INSUFFICIENT_DURATION_S",
    "INSUFFICIENT_PHONEMES",
    "build_signal",
    "display_label_from",
    "phoneme_error_rate",
    "reference_phonemes",
]
