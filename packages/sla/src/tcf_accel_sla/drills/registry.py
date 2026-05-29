"""Drill registry — maps a `DrillKind` to its `Drill` implementation.

Phase 5 lands drills incrementally (`phase5_design.md §17`). A kind that
hasn't been implemented yet is simply absent from `REGISTRY`;
`get_drill` raises `NotImplementedError` naming the kind, so the
session lifecycle fails loudly rather than silently mis-grading.
"""

from __future__ import annotations

from tcf_accel.schemas.api.plan import DrillKind, DrillType
from tcf_accel.schemas.item import Module

from tcf_accel_sla.drills.base import Drill
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

# Singleton drill instances (drills are stateless; one instance suffices).
REGISTRY: dict[DrillKind, Drill] = {
    "co_mcq": COMCQDrill(),
    "co_dictation": CODictationDrill(),
    "co_gapfill": COGapFillDrill(),
    "co_lexical_alt": COLexicalAltDrill(),
    "ce_mcq": CEMCQDrill(),
    "ee_task": EETaskDrill(),
    "ee_rewrite": EERewriteDrill(),
    "ee_register_adjust": EERegisterAdjustDrill(),
    "eo_task": EOTaskDrill(),
    "eo_picture": EOPictureDrill(),
    "eo_spontaneous": EOSpontaneousDrill(),
    "eo_roleplay": EORoleplayDrill(),
    "eo_repair": EORepairDrill(),
    "eo_text_alt": EOTextAltDrill(),
}

# Maps the coarse (module, DrillType) the planner emits in a PlanBlock to
# the finer DrillKind the lifecycle runs. A DrillType that is already a
# DrillKind (the Phase 5 names like "co_dictation") maps to itself.
# Phase 5 lands these incrementally; unmapped pairs fall through to
# `get_drill`, which raises NotImplementedError.
_MODULE_DRILLTYPE_TO_KIND: dict[tuple[Module, DrillType], DrillKind] = {
    ("CO", "mcq"): "co_mcq",
    ("CE", "mcq"): "ce_mcq",
    # The Phase 1–4 legacy names for the timed-production drills:
    # writing_short → Task 1 (60 w / 10 min), writing_long → Task 3 (180 w / 30 min).
    # Both currently resolve to `ee_task`; the per-task parameters come
    # from the item's `EEContent.task_number`.
    ("EE", "writing_short"): "ee_task",
    ("EE", "writing_long"): "ee_task",
    # speaking_mono → core EO task (Q&A / describe / argue); the per-task
    # parameters come from EOContent.task_number.
    # speaking_role → role-play with TTS interlocutor.
    ("EO", "speaking_mono"): "eo_task",
    ("EO", "speaking_role"): "eo_roleplay",
}


def get_drill(kind: DrillKind) -> Drill:
    """Return the drill implementation for `kind`.

    Raises:
        NotImplementedError: if `kind` is a valid `DrillKind` that
            Phase 5 has not yet implemented (e.g. an EO drill before
            its implementation step lands).

    Example:
        >>> get_drill("co_mcq").spec.module
        'CO'
    """
    try:
        return REGISTRY[kind]
    except KeyError:
        msg = f"drill kind {kind!r} is not yet implemented (phase5_design.md §17)"
        raise NotImplementedError(msg) from None


def resolve_drill_kind(module: Module, drill_type: DrillType) -> DrillKind:
    """Map a planner `(module, DrillType)` to the concrete `DrillKind`.

    A `DrillType` that is itself a Phase 5 `DrillKind` (e.g.
    `"co_dictation"`) maps to itself; the coarse legacy names
    (`"mcq"`, `"shadowing"`, …) map via the module discriminator.

    Raises:
        NotImplementedError: if no kind is registered for the pair.

    Example:
        >>> resolve_drill_kind("CO", "mcq")
        'co_mcq'
    """
    mapped = _MODULE_DRILLTYPE_TO_KIND.get((module, drill_type))
    if mapped is not None:
        return mapped
    # The drill_type may already be a fully-qualified DrillKind.
    if drill_type in REGISTRY:
        return drill_type  # type: ignore[return-value]
    msg = (
        f"no drill kind registered for module={module!r}, "
        f"drill_type={drill_type!r} (phase5_design.md §17)"
    )
    raise NotImplementedError(msg)


__all__ = ["REGISTRY", "get_drill", "resolve_drill_kind"]
