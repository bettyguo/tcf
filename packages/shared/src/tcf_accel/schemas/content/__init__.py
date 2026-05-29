"""Module-specific item content variants.

Phase 2 narrows the Phase 1 permissive `ItemContent` placeholder into a
discriminated union (`COContent | CEContent | EEContent | EOContent`)
keyed on the `module` discriminator. See `02_ARCHITECTURE.md §2.3`,
`phase2_design.md §3.1`, ADR-0011.

The narrowing is additive: any Phase 1 instance that already carried a
`module` field matching one of `{CO, CE, EE, EO}` continues to validate
against the new union.
"""

from __future__ import annotations

from tcf_accel.schemas.content.ce import CEContent
from tcf_accel.schemas.content.co import COContent, MCQ, MCQOption, Speaker
from tcf_accel.schemas.content.ee import EEContent, ErrorAnnotation
from tcf_accel.schemas.content.eo import EOContent

__all__ = [
    "CEContent",
    "COContent",
    "EEContent",
    "EOContent",
    "ErrorAnnotation",
    "MCQ",
    "MCQOption",
    "Speaker",
]
