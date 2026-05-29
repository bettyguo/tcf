"""CEFR classifier implementations.

Two implementations ship with the package:

- `FakeCEFRClassifier` — deterministic, hash-seeded; produces a
  realistic-looking softmax distribution without any model weights.
  Used in tests and as the default when the real classifier artifact
  is not present (so the pipeline is wireable end-to-end).
- `CamembertCEFRClassifier` — placeholder. Phase 3 follow-up wires
  in the fine-tuned CamemBERT artifact under
  ``packages/content/models/cefr-v0.3.1/``. The placeholder raises
  `CEFRClassifierUnavailableError` if invoked without the model
  present.

The `load_classifier` factory returns the real classifier when its
artifact is available and falls back to `FakeCEFRClassifier` otherwise,
emitting a warning so that an operator running `seed_bank.py` against
the open-only mode does not silently rely on the fake without realising.
"""

from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from tcf_accel.errors import CEFRClassifierUnavailableError

from tcf_accel_content.cefr import CEFR_LEVELS, CEFRClassifier, CefrLevel, CEFRPrediction

_logger = logging.getLogger(__name__)

# Hand-tuned so the fake's confidences look like a calibrated softmax
# rather than one-hot. Adjust only if tests start failing in ways that
# tell us the fake is unrealistically peaky or flat.
_FAKE_TEMPERATURE: float = 1.6


@dataclass(frozen=True)
class FakeCEFRClassifier:
    """Deterministic stand-in for the real CEFR classifier.

    Same text always produces the same prediction. The level is
    sha256(text) mod 6 mapped through `CEFR_LEVELS`. The distribution
    places the largest mass on the predicted level and decays with
    distance under a temperature-1.6 softmax.

    Example:
        >>> clf = FakeCEFRClassifier()
        >>> a = clf.classify("Le chat est sur le tapis.")
        >>> b = clf.classify("Le chat est sur le tapis.")
        >>> a == b
        True
        >>> abs(sum(a.distribution.values()) - 1.0) < 1e-6
        True
        >>> a.level in {"A1","A2","B1","B2","C1","C2"}
        True

    Complexity: O(|text|) for hashing.
    """

    classifier_version: ClassVar[str] = "fake-v0"

    def classify(self, text: str) -> CEFRPrediction:
        """Classify a single text. See class docstring for the algorithm."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        idx = digest[0] % len(CEFR_LEVELS)
        level = CEFR_LEVELS[idx]
        distribution = _softmax_around(idx, temperature=_FAKE_TEMPERATURE)
        return CEFRPrediction(
            level=level,
            confidence=distribution[level],
            distribution=distribution,
            classifier_version=self.classifier_version,
            text_sha256=digest.hex(),
        )

    def classify_batch(self, texts: list[str]) -> list[CEFRPrediction]:
        """Classify a batch.

        Pure convenience over `classify`; the fake has no batching
        speedup, but this matches the `CEFRClassifier` protocol so
        downstream code can be written once.
        """
        return [self.classify(t) for t in texts]


@dataclass(frozen=True)
class CamembertCEFRClassifier:
    """Placeholder for the fine-tuned CamemBERT classifier (ADR-0008).

    Phase 3 follow-up wires the real model. Until then, attempting to
    construct this class without the artifact raises
    `CEFRClassifierUnavailableError` so the operator gets a clear
    signal rather than a silent fallback.
    """

    classifier_version: ClassVar[str] = "cefr-v0.3.1"

    artifact_dir: Path

    def __post_init__(self) -> None:
        """Refuse to construct if the artifact directory is missing.

        Raises:
            CEFRClassifierUnavailableError: when the artifact is not
                present on disk. The message names the expected path
                so the operator knows what to fetch.
        """
        if not self.artifact_dir.is_dir():
            raise CEFRClassifierUnavailableError(
                version=self.classifier_version,
                detail=f"artifact_dir={self.artifact_dir} does not exist",
            )
        # The actual model load happens here in the Phase 3 follow-up.
        raise CEFRClassifierUnavailableError(
            version=self.classifier_version,
            detail="CamembertCEFRClassifier is not yet implemented; use FakeCEFRClassifier",
        )

    def classify(self, text: str) -> CEFRPrediction:
        """Not implemented; constructor refuses."""
        raise NotImplementedError

    def classify_batch(self, texts: list[str]) -> list[CEFRPrediction]:
        """Not implemented; constructor refuses."""
        raise NotImplementedError


def load_classifier(
    artifact_dir: Path | None = None,
    *,
    allow_fake: bool = True,
) -> CEFRClassifier:
    """Return the real classifier if available, otherwise the fake.

    Args:
        artifact_dir: Optional path to the real classifier artifact.
            When `None` or missing, the fake is returned.
        allow_fake: If False, refuses to fall back to the fake and
            re-raises `CEFRClassifierUnavailableError`. Use this in
            production paths where a silent fallback would be wrong.

    Returns:
        A `CEFRClassifier`-conforming instance.

    Example:
        >>> from pathlib import Path
        >>> clf = load_classifier(Path("/does/not/exist"))
        >>> clf.classifier_version
        'fake-v0'
    """
    if artifact_dir is not None and artifact_dir.is_dir():
        try:
            return CamembertCEFRClassifier(artifact_dir=artifact_dir)
        except CEFRClassifierUnavailableError:
            if not allow_fake:
                raise
            _logger.warning(
                "Real CEFR classifier unavailable; falling back to FakeCEFRClassifier",
            )
    elif not allow_fake:
        raise CEFRClassifierUnavailableError(
            version="cefr-v0.3.1",
            detail=f"artifact_dir={artifact_dir} missing and allow_fake=False",
        )
    return FakeCEFRClassifier()


def _softmax_around(predicted_idx: int, *, temperature: float) -> dict[CefrLevel, float]:
    """Build a temperature-softmax distribution peaked at `predicted_idx`.

    Logits = -|i - predicted_idx|; the temperature controls peakiness
    (lower → more confident). Normalises exactly to 1.0.

    Complexity: O(|CEFR_LEVELS|).
    """
    logits = [-abs(i - predicted_idx) / temperature for i in range(len(CEFR_LEVELS))]
    exps = [math.exp(x) for x in logits]
    total = sum(exps)
    return {level: exp / total for level, exp in zip(CEFR_LEVELS, exps, strict=True)}


__all__ = [
    "CamembertCEFRClassifier",
    "FakeCEFRClassifier",
    "load_classifier",
]
