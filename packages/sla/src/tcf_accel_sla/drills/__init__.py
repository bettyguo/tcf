"""Drill engines (`05_PRACTICE_AND_DRILLS.md §2`, `phase5_design.md §4`).

One module per drill kind. Each drill is a `Drill` subclass that knows
how to (a) present an `Item`, (b) grade a learner response, and (c)
project the graded result into a typed `Interaction` row. The
`Interaction` write path is the single funnel into the learner model
(Phase 4 consumes it); no drill writes to the DB directly.

The drill *logic* is pure-stdlib — ML calls (Whisper, MFA, TTS) live
behind ports in `tcf_accel_ml` so this package keeps the Phase 4
zero-runtime-dependency posture and `make verify` passes in an empty
venv.

Phase 5 ships the registry incrementally; `get_drill(kind)` raises
`NotImplementedError` for kinds whose module hasn't landed yet.
"""

from __future__ import annotations

from tcf_accel_sla.drills.base import (
    Drill,
    DrillResult,
    DrillSpec,
    DrillStep,
    grade_mcq,
)
from tcf_accel_sla.drills.ce_mcq import CEMCQDrill
from tcf_accel_sla.drills.co_dictation import CODictationDrill
from tcf_accel_sla.drills.co_gapfill import COGapFillDrill
from tcf_accel_sla.drills.co_lexical_alt import COLexicalAltDrill
from tcf_accel_sla.drills.co_mcq import COMCQDrill
from tcf_accel_sla.drills.ee_register_adjust import EERegisterAdjustDrill
from tcf_accel_sla.drills.ee_rewrite import EERewriteDrill
from tcf_accel_sla.drills.ee_task import EETaskDrill
from tcf_accel_sla.drills.eo_picture import EOPictureDrill
from tcf_accel_sla.drills.eo_repair import EORepairDrill
from tcf_accel_sla.drills.eo_roleplay import EORoleplayDrill
from tcf_accel_sla.drills.eo_spontaneous import EOSpontaneousDrill
from tcf_accel_sla.drills.eo_task import EOTaskDrill
from tcf_accel_sla.drills.eo_text_alt import EOTextAltDrill
from tcf_accel_sla.drills.registry import REGISTRY, get_drill, resolve_drill_kind

__all__ = [
    "REGISTRY",
    "CEMCQDrill",
    "CODictationDrill",
    "COGapFillDrill",
    "COLexicalAltDrill",
    "COMCQDrill",
    "Drill",
    "DrillResult",
    "DrillSpec",
    "DrillStep",
    "EERegisterAdjustDrill",
    "EERewriteDrill",
    "EETaskDrill",
    "EOPictureDrill",
    "EORepairDrill",
    "EORoleplayDrill",
    "EOSpontaneousDrill",
    "EOTaskDrill",
    "EOTextAltDrill",
    "get_drill",
    "grade_mcq",
    "resolve_drill_kind",
]
