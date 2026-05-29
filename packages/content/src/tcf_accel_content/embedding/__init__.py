"""Embedding + HDBSCAN clustering for the bank.

`embed.py` produces multilingual-MPNet vectors matching the Phase 2
`items.embedding VECTOR(768)` column; `cluster.py` runs HDBSCAN over
the bank to compute `topic_cluster_id` per item, feeding the 5%-cap
audit (ADR-0022).
"""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

EMBEDDER_MODEL: str = (
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
EMBEDDER_DIM: int = 768  # matches items.embedding VECTOR(768)
EMBEDDER_VERSION: str = "mpnet-v2.0"

# HDBSCAN params (phase3_design.md §6.2)
HDBSCAN_MIN_CLUSTER_SIZE: int = 8
HDBSCAN_METRIC: str = "cosine"

TOPIC_CLUSTER_CAP: float = 0.05  # ADR-0022 / phase3_design.md §6.3


@runtime_checkable
class Embedder(Protocol):
    """Phase-3 embedder interface; stubbed in tests."""

    embedder_version: ClassVar[str]
    embedder_dim: ClassVar[int]

    def embed(self, text: str) -> list[float]:
        """Embed one text into an L2-normalised vector of length `embedder_dim`."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch; implementations may share encoder state."""
        ...


__all__ = [
    "EMBEDDER_DIM",
    "EMBEDDER_MODEL",
    "EMBEDDER_VERSION",
    "HDBSCAN_METRIC",
    "HDBSCAN_MIN_CLUSTER_SIZE",
    "TOPIC_CLUSTER_CAP",
    "Embedder",
]
