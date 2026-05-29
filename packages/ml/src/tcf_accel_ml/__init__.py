"""ML services for tcf-accel.

Phase 5 step 6 (`phase5_design.md §2`, §5, §6) populates this with:

- `tcf_accel_ml.asr`        — ASR backends (local Whisper-fr, cloud
  LiteLLM opt-in, deterministic stub).
- `tcf_accel_ml.alignment`  — Montreal Forced Aligner wrapper + stub.
- `tcf_accel_ml.prosody`    — pitch / pause / speech-rate analyzers
  that compose into `PronunciationProsody`.

Backend dispatch reads `TCF_ACCEL_ASR_BACKEND` / `TCF_ACCEL_MFA_BACKEND`
env vars. Default is local (CPU); no learner audio crosses the network
without an explicit operator opt-in (ADR-017).

Heavy runtime deps (faster-whisper, librosa, the `mfa` binary) are
lazy-imported / lazy-invoked: the package stays importable in a clean
venv. `make install-models` is the operator step that populates the
weights + binaries for production use.
"""

from __future__ import annotations

__version__ = "0.2.0"
