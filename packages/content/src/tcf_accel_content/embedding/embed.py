"""Embedder implementations.

`FakeEmbedder` produces a 768-dim L2-normalised vector deterministic
from sha256(text), with no model weights. It is used for tests and as
the default when the real sentence-transformers model is not on disk —
this lets the pipeline (and its tests) run end-to-end without
downloading ~500 MB of weights.

`MPNetEmbedder` is the real implementation (Phase 3 follow-up); the
placeholder here raises a clear error if invoked.

The fake is implemented with stdlib only (`hashlib` + `random.Random`)
so this module has no numpy / torch / sentence-transformers
dependency at this stage.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import ClassVar

from tcf_accel_content.embedding import EMBEDDER_DIM, Embedder


@dataclass(frozen=True)
class FakeEmbedder:
    """Deterministic stand-in for the multilingual MPNet embedder.

    Hashes the text, uses the hash to seed a `random.Random`, draws
    `EMBEDDER_DIM` Gaussian samples, and L2-normalises. Same text
    always produces the same vector; different texts produce different
    vectors (collisions are sha256-rare).

    Example:
        >>> e = FakeEmbedder()
        >>> v1 = e.embed("bonjour")
        >>> v2 = e.embed("bonjour")
        >>> v1 == v2
        True
        >>> len(v1) == 768
        True
        >>> abs(sum(x * x for x in v1) - 1.0) < 1e-9
        True

    Complexity: O(EMBEDDER_DIM) for the vector draw + normalisation.
    """

    embedder_version: ClassVar[str] = "fake-v0"
    embedder_dim: ClassVar[int] = EMBEDDER_DIM

    def embed(self, text: str) -> list[float]:
        """Embed a single text into a normalised vector."""
        seed = int.from_bytes(
            hashlib.sha256(text.encode("utf-8")).digest()[:8], "big", signed=False,
        )
        rng = random.Random(seed)  # noqa: S311 - not used for security
        # Box-Muller via random.gauss; rng is locally seeded so calls
        # are deterministic across runs and process restarts.
        raw = [rng.gauss(0.0, 1.0) for _ in range(self.embedder_dim)]
        norm = math.sqrt(sum(x * x for x in raw))
        if norm == 0.0:
            # Astronomically unlikely with 768 draws; defend anyway.
            raw[0] = 1.0
            norm = 1.0
        return [x / norm for x in raw]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts; no batching speedup over `embed`."""
        return [self.embed(t) for t in texts]


@dataclass(frozen=True)
class MPNetEmbedder:
    """Placeholder for the real multilingual MPNet embedder.

    Phase 3 follow-up wires `sentence-transformers/paraphrase-
    multilingual-mpnet-base-v2`. Until then, construction raises
    `NotImplementedError` to make the silent-fallback risk obvious.
    """

    embedder_version: ClassVar[str] = "mpnet-v2.0"
    embedder_dim: ClassVar[int] = EMBEDDER_DIM

    def __post_init__(self) -> None:
        """Refuse to construct until the real impl lands."""
        raise NotImplementedError(
            "MPNetEmbedder is not yet implemented; use FakeEmbedder for tests "
            "and wait for the Phase 3 follow-up that wires sentence-transformers.",
        )

    def embed(self, text: str) -> list[float]:
        """Not implemented; constructor refuses."""
        raise NotImplementedError

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Not implemented; constructor refuses."""
        raise NotImplementedError


def load_embedder(*, allow_fake: bool = True) -> Embedder:
    """Return the real embedder if available, otherwise the fake.

    Args:
        allow_fake: If False, refuses to fall back; useful in
            production paths where a silent fake would be wrong.

    Returns:
        An `Embedder`-conforming instance.
    """
    try:
        return MPNetEmbedder()
    except NotImplementedError:
        if not allow_fake:
            raise
    return FakeEmbedder()


__all__ = ["FakeEmbedder", "MPNetEmbedder", "load_embedder"]
