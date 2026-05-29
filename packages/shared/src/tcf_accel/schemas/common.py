"""Common schemas reused across modules.

`Provenance` is the chain-of-custody record for every item; `QualityFlag` is
the union of pipeline-stage flags; `ItemMetadata` is the open-ended bag of
tags for retrieval and analytics.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReviewStatus = Literal[
    "auto_passed",
    "human_approved",
    "human_modified",
    "rejected",
    "pending_review",
]


class QualityFlag(str, Enum):
    """Pipeline-stage flags attached to an item.

    These are *informational*; pipeline stages may reject on certain flags,
    but the flag itself is data, not a decision.
    """

    SYNTHETIC = "synthetic"
    LOW_CONFIDENCE_CEFR = "low_confidence_cefr"
    POTENTIAL_DUPLICATE = "potential_duplicate"
    HIGH_ADVERSARIAL = "high_adversarial"
    PII_SUSPECTED = "pii_suspected"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    LICENSE_AMBIGUOUS = "license_ambiguous"
    ACOUSTIC_LOW_QUALITY = "acoustic_low_quality"
    REGISTER_MISMATCH = "register_mismatch"
    CEFR_HUMAN_OVERRIDDEN = "cefr_human_overridden"
    TOPIC_OVER_CAPPED = "topic_over_capped"


class Provenance(BaseModel):
    """Chain-of-custody for an item.

    Every item carries one of these. The fields are deliberately verbose so
    `audit-content` (Phase 3+) can reconstruct any item's origin without
    consulting external systems.

    Example:
        >>> from datetime import UTC, datetime
        >>> Provenance(
        ...     source="common_voice_fr_v17",
        ...     source_id="19284732",
        ...     license="CC0-1.0",
        ...     ingested_at=datetime(2026, 6, 1, tzinfo=UTC),
        ...     review_status="auto_passed",
        ... ).license
        'CC0-1.0'

    Complexity: O(1) construction.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    source: str = Field(description="Logical source identifier, e.g. 'common_voice_fr_v17'.")
    source_id: str = Field(description="Stable id within the source.")
    license: str = Field(
        description="SPDX-style identifier (e.g. 'CC0-1.0', 'CC-BY-SA-4.0') "
        "or 'proprietary' for unredistributable items.",
    )
    ingested_at: datetime = Field(description="UTC timestamp of ingestion.")
    fetcher_version: str | None = None
    synthesizer_version: str | None = None
    llm_model: str | None = None
    llm_prompt_hash: str | None = Field(
        default=None,
        description="sha256 of the rendered LLM prompt; used for reproducibility audits.",
    )
    review_status: ReviewStatus = "auto_passed"
    review_notes: str | None = None


class ItemMetadata(BaseModel):
    """Open-ended metadata bag for retrieval, clustering, and analytics.

    The model remains `extra="allow"`, so any field not listed here is
    accepted and round-trips through the JSONB column. The fields
    enumerated below are *documented* surfaces — populated by the
    Phase 3 content pipeline and consumed by Phase 4+. Adding a new
    optional field here is a non-breaking change.
    """

    model_config = ConfigDict(extra="allow")

    topic: str | None = None
    topic_cluster_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    created_by: str | None = None
    seed: int | None = Field(
        default=None,
        description="Deterministic seed used during synthesis; enables reproducibility.",
    )
    # ─── Phase 3 additive surfaces (all optional) ──────────────
    cefr_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Max-softmax post-calibration probability from the CEFR classifier.",
    )
    cefr_distribution: dict[str, float] | None = Field(
        default=None,
        description="Full A1..C2 softmax distribution at the time the item was classified.",
    )
    canadian_context: bool | None = Field(
        default=None,
        description="True iff the item's content is Canadian-flavored (EE/EO Tasks 2&3 require True).",
    )
    co_acoustic: dict[str, float] | None = Field(
        default=None,
        description=(
            "CO-only acoustic features: keys 'speech_rate_wpm', 'lexical_density', "
            "'n_speakers_diarized', 'noisiness_proxy'."
        ),
    )
    calibration_anchors: dict[str, str] | None = Field(
        default=None,
        description=(
            "EE/EO-only model-response anchors keyed by 'nclc_7', 'nclc_9', 'nclc_11'; "
            "Phase 7 calibrates the rubric scorer against these."
        ),
    )
    synthesis_trace_uri: str | None = Field(
        default=None,
        description="Local-only pointer to data/cache/quality/<item_id>.json with the full synthesis trace.",
    )
