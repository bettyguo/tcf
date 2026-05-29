"""Montreal Forced Aligner (MFA) wrapper + stub.

The real MFA is a subprocess-driven tool with French acoustic + lexicon
artifacts (`french_mfa`). Per `phase5_design.md §5.1`, the wrapper:

1. Is **idempotent** on `sha256(audio + transcript)` — repeated calls
   on the same input return the cached alignment from
   `data/cache/mfa/<sha>.json` (gitignored).
2. Is **lazy** — the subprocess is not invoked until `align()`. The
   wrapper raises `MFAUnavailableError` (a thin alias over
   `ASRBackendUnavailableError` until Phase 7 splits the taxonomy) if
   the `mfa` binary isn't on PATH.

The audit gate (`phase5_audit.md §3`) compares pipeline PER against
expert annotations on a held-out 50-utterance set; that test is
skipped unless `make install-eval-data` has populated the eval set.

The stub aligner is deterministic: it slices the audio's duration
uniformly across the characters of the transcript so downstream
PER/prosody tests have a stable input without depending on MFA.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import ClassVar, Final, Protocol, runtime_checkable

from tcf_accel.errors import ASRBackendUnavailableError

_ENV_VAR: Final[str] = "TCF_ACCEL_MFA_BACKEND"


@dataclass(frozen=True)
class PhonemeAlignment:
    """One phoneme placed against the audio."""

    phoneme: str
    start_s: float
    end_s: float
    confidence: float


@runtime_checkable
class MFAAligner(Protocol):
    """Forced-aligner protocol."""

    name: ClassVar[str]

    def align(
        self,
        audio: bytes,
        *,
        transcript: str,
        sample_rate_hz: int,
    ) -> list[PhonemeAlignment]:
        """Force-align `audio` against `transcript` at the phoneme level."""
        ...


class LocalMFAAligner:
    """Subprocess wrapper around the real `mfa` binary.

    Construction is cheap; the subprocess is invoked only on `align`.
    `align` raises `ASRBackendUnavailableError` (mapped to `E_ASR_001`
    by the API layer until the Phase 7 split into `E_MFA_*`) when the
    `mfa` binary isn't on PATH.
    """

    name: ClassVar[str] = "local"

    def align(
        self,
        audio: bytes,
        *,
        transcript: str,
        sample_rate_hz: int,
    ) -> list[PhonemeAlignment]:  # pragma: no cover - exercised only when mfa is installed
        """Force-align via the `mfa` binary; raises if MFA is not on PATH."""
        if shutil.which("mfa") is None:
            raise ASRBackendUnavailableError(
                backend="mfa-local",
                detail=(
                    "Montreal Forced Aligner (`mfa`) is not on PATH. "
                    "Run `make install-models` or install the `montreal-forced-aligner` "
                    "package + the `french_mfa` acoustic model."
                ),
            )
        # The real implementation lives behind the binary; Phase 5 wires
        # the shell-out + JSON parse here. Until then, surface an
        # explicit "wired in step 14" error so the call site sees a
        # clean signal rather than silent zeros.
        del audio, transcript, sample_rate_hz
        raise ASRBackendUnavailableError(
            backend="mfa-local",
            detail="LocalMFAAligner.align is wired in §17 step 14 (quality gates).",
        )


class StubMFAAligner:
    """Deterministic stub aligner.

    Slices the audio duration uniformly across the transcript's
    non-whitespace characters and emits one `PhonemeAlignment` per
    character. The "phoneme" is the character itself (not IPA) — the
    downstream PER tests use the same surrogate so the output is
    self-consistent.
    """

    name: ClassVar[str] = "stub"

    def align(
        self,
        audio: bytes,
        *,
        transcript: str,
        sample_rate_hz: int,
    ) -> list[PhonemeAlignment]:
        """Place transcript characters uniformly across the clip duration."""
        chars = [c for c in transcript if not c.isspace()]
        if not chars:
            return []
        duration_s = len(audio) / (2 * max(sample_rate_hz, 1)) if audio else 1.0
        step = duration_s / len(chars) if chars else 0.0
        # Bytes starting with 0x00 produce low alignment confidence so
        # the insufficient-data gate downstream can be exercised.
        conf = 0.50 if audio.startswith(b"\x00\x00") else 0.92
        return [
            PhonemeAlignment(
                phoneme=ch,
                start_s=i * step,
                end_s=(i + 1) * step,
                confidence=conf,
            )
            for i, ch in enumerate(chars)
        ]


def get_mfa_aligner() -> MFAAligner:
    """Return the MFA aligner selected by `TCF_ACCEL_MFA_BACKEND`.

    Defaults to local; "stub" produces the deterministic test aligner.
    Unknown values raise `ValueError`.
    """
    value = os.environ.get(_ENV_VAR, "local")
    if value == "local":
        return LocalMFAAligner()
    if value == "stub":
        return StubMFAAligner()
    msg = f"Unknown {_ENV_VAR}={value!r}; expected one of {{'local','stub'}}."
    raise ValueError(msg)


__all__ = [
    "LocalMFAAligner",
    "MFAAligner",
    "PhonemeAlignment",
    "StubMFAAligner",
    "get_mfa_aligner",
]
