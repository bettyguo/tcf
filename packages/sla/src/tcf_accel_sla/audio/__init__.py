"""Audio pipeline facade for the EO drills (`phase5_design.md §3`, §5).

The drill engines compose ASR → MFA → prosody → `PronunciationSignal`
end-to-end. This module is the SLA-side seam: it lazy-imports
`tcf_accel_ml` so the `tcf_accel_sla.drills` package stays importable
in a venv that doesn't yet have the ML deps. Tests run against the
stub backends by setting `TCF_ACCEL_{ASR,MFA}_BACKEND=stub`.
"""

from __future__ import annotations

from tcf_accel_sla.audio.pipeline import (
    AudioPipelineOutputs,
    run_audio_pipeline,
)

__all__ = ["AudioPipelineOutputs", "run_audio_pipeline"]
