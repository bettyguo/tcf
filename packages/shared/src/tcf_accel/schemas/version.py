"""Cross-package schema version.

Bumped on every breaking change to the schemas under `tcf_accel.schemas`.
Phase 1 baselines at 0.1.0. Additive changes (Phase 2 narrowing of
`ItemContent`, additional rubric fields in Phase 7) bump minor.
"""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final[str] = "0.1.0"

__all__ = ["SCHEMA_VERSION"]
