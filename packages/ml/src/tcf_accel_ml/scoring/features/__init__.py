"""Feature extraction for the Phase 7 rubric scorers.

Pure-Python: no spaCy/numpy at import time. The features are bounded,
deterministic, and computed in linear time over the input string.
"""

from __future__ import annotations

from tcf_accel_ml.scoring.features.canadian import canadian_lexicon_density
from tcf_accel_ml.scoring.features.connectors import (
    discourse_marker_counts,
    distinct_discourse_categories,
)
from tcf_accel_ml.scoring.features.errors import (
    HeuristicErrorDetector,
    detect_errors,
)
from tcf_accel_ml.scoring.features.register import register_score
from tcf_accel_ml.scoring.features.speaking import (
    SpeakingFeatures,
    extract_speaking_features,
)
from tcf_accel_ml.scoring.features.writing import (
    WritingFeatures,
    extract_writing_features,
)

__all__ = [
    "HeuristicErrorDetector",
    "SpeakingFeatures",
    "WritingFeatures",
    "canadian_lexicon_density",
    "detect_errors",
    "discourse_marker_counts",
    "distinct_discourse_categories",
    "extract_speaking_features",
    "extract_writing_features",
    "register_score",
]
