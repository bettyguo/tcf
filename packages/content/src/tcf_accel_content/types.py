"""Shared types for the content pipeline.

These are *pipeline-internal* shapes — wrappers around the frozen
contract types in `tcf_accel.schemas`. The pipeline serializes its
outputs *down* to `tcf_accel.schemas.Item` for storage; the wrappers
exist to carry stage traces and intermediate metadata that the DB does
not need.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from tcf_accel.schemas import Item, Provenance

RawKind = Literal["audio", "text"]


@dataclass(frozen=True)
class RawAsset:
    """One unit of raw input from a source module.

    `bytes_` is set when `kind == 'audio'`; `text` is set when
    `kind == 'text'`. Exactly one is non-None.
    """

    kind: RawKind
    source: str
    source_id: str
    license: str
    fetched_at: datetime
    text: str | None = None
    bytes_: bytes | None = None
    bytes_path: Path | None = None
    ground_truth_transcript: str | None = None
    extra: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the kind-specific payload requirement."""
        if self.kind == "audio" and self.bytes_ is None and self.bytes_path is None:
            raise ValueError("audio RawAsset requires bytes_ or bytes_path")
        if self.kind == "text" and self.text is None:
            raise ValueError("text RawAsset requires text")


@dataclass(frozen=True)
class SynthesisTrace:
    """Per-item trace of the synthesis call(s).

    Persisted to `data/cache/quality/<item_id>.json` for audit and
    reproducibility (phase3_design.md §3, §5, §9).
    """

    model: str
    prompt_hash: str
    response_hash: str
    latency_ms: float
    tokens_in: int
    tokens_out: int
    retries: int = 0
    seed: int | None = None


@dataclass(frozen=True)
class CandidateItem:
    """A synthesizer output before the quality gate has run.

    The wrapped `item` is Pydantic-valid; the `trace` is what the gate
    and audit consume separately. Once the gate passes, the loader
    persists `item` (and the trace URI is written into
    `item.metadata.synthesis_trace_uri`).
    """

    item: Item
    trace: SynthesisTrace
    passage_provenance: Provenance | None = None


@dataclass(frozen=True)
class QualityCheckResult:
    """Outcome of a single gate check (`phase3_design.md §5`).

    `metric` is the numeric value the check measured (e.g. adversarial
    accuracy, distractor-length delta) when applicable; `None` for
    pass/fail-only checks.
    """

    name: str
    passed: bool
    severity: Literal["P0", "P1", "info"]
    detail: str | None = None
    metric: float | None = None


@dataclass(frozen=True)
class QualityReport:
    """Outcome of the gate. `verdict` is what the loader trusts."""

    item_id: str
    checks: tuple[QualityCheckResult, ...]
    verdict: Literal["pass", "p1_flag", "reject"]
    flags: tuple[str, ...] = ()


__all__ = [
    "CandidateItem",
    "QualityCheckResult",
    "QualityReport",
    "RawAsset",
    "RawKind",
    "SynthesisTrace",
]
