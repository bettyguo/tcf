"""CEFR classification: text-level + acoustic adjustment.

`classify.py` (Phase 3 implementation) wraps a fine-tuned CamemBERT
classifier (ADR-0008). This module ships the `CEFRClassifier` protocol
and the `CEFRPrediction` dataclass.

Audit gates (`phase3_design.md §4.6`):
- macro-F1 ≥ 0.72 on the 500-item validation set
- adjacent-level accuracy ≥ 0.93
- ECE ≤ 0.10 (target ≤ 0.05 post-temperature-scaling)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal, Protocol, runtime_checkable

CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
CEFR_LEVELS: tuple[CefrLevel, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")


@dataclass(frozen=True)
class CEFRPrediction:
    """A single CEFR classification with calibrated confidence.

    `distribution` is the full A1..C2 softmax (sums to 1.0 ± floating
    error). `text_sha256` is the fingerprint of the classified input.
    """

    level: CefrLevel
    confidence: float
    distribution: dict[CefrLevel, float]
    classifier_version: str
    text_sha256: str


@runtime_checkable
class CEFRClassifier(Protocol):
    """The Phase-3 CEFR classifier interface.

    Phase 3 ships `CamembertCEFRClassifier` as the default impl.
    Phase 4+ stubs this in tests via a deterministic fake.
    """

    classifier_version: ClassVar[str]

    def classify(self, text: str) -> CEFRPrediction:
        """Classify one text into a calibrated CEFR prediction."""
        ...

    def classify_batch(self, texts: list[str]) -> list[CEFRPrediction]:
        """Classify a batch; implementations may parallelise."""
        ...


__all__ = [
    "CEFR_LEVELS",
    "CEFRClassifier",
    "CEFRPrediction",
    "CefrLevel",
]
