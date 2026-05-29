"""Forced-alignment subpackage (`phase5_design.md §5.1`).

Aligns ASR transcripts against the audio at the phoneme level so the
pronunciation pipeline can compute a phoneme-error-rate against a
canonical reference.

The real implementation wraps Montreal Forced Aligner (MFA), a
subprocess-driven tool with its own French acoustic model + dictionary
(`french_mfa`). The wrapper is lazy: it doesn't shell out at import
time, so the package stays importable in environments where MFA isn't
installed.

The stub aligner is deterministic and dependency-free; downstream
pipeline tests use it.
"""

from __future__ import annotations

from tcf_accel_ml.alignment.mfa import (
    LocalMFAAligner,
    MFAAligner,
    PhonemeAlignment,
    StubMFAAligner,
    get_mfa_aligner,
)

__all__ = [
    "LocalMFAAligner",
    "MFAAligner",
    "PhonemeAlignment",
    "StubMFAAligner",
    "get_mfa_aligner",
]
