"""License-compatibility quality check.

A P0 gate (`phase3_design.md §5.1`): an item whose provenance carries a
non-allowlisted license is rejected before it ever reaches the bank.
The allowlist itself lives at `sources.REDISTRIBUTABLE_LICENSE_ALLOWLIST`
so source modules and gate checks share one source of truth.

Operator-tier items (RFI, ICI Première, etc.) carry source-specific
license strings (e.g. ``"RFI-TOS-personal-study"``); those are *not* in
the allowlist and so are rejected for repo-redistribution paths. The
operator's local bank can keep them by setting `permit_local_only=True`,
which downgrades the check from P0-reject to P1-flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tcf_accel.schemas import Item

from tcf_accel_content.sources import license_compatible
from tcf_accel_content.types import QualityCheckResult


@dataclass(frozen=True)
class LicenseCompatibleCheck:
    """P0 check: item's `provenance.license` is in the allowlist.

    Args:
        permit_local_only: When True, a non-allowlisted license
            downgrades from P0-reject to P1-flag. Operators may set
            this for local-only banks where redistribution is not in
            scope. Default False (the repo's posture).

    Example:
        >>> from datetime import UTC, datetime
        >>> from uuid import uuid4
        >>> from tcf_accel.ids import ItemId
        >>> from tcf_accel.schemas import (
        ...     CEContent, Item, MCQ, MCQOption, Provenance,
        ... )
        >>> def _item(license: str) -> Item:
        ...     return Item(
        ...         id=ItemId(uuid4()), module="CE", cefr_level="B2",
        ...         content=CEContent(
        ...             passage="x" * 60, genre="news", word_count=12,
        ...             questions=[MCQ(
        ...                 id="q1", prompt="?",
        ...                 options=[MCQOption(id="a", text="a"),
        ...                          MCQOption(id="b", text="b")],
        ...                 correct_option_id="a",
        ...             )],
        ...         ),
        ...         provenance=Provenance(
        ...             source="x", source_id="1", license=license,
        ...             ingested_at=datetime(2026,1,1,tzinfo=UTC),
        ...         ),
        ...     )
        >>> check = LicenseCompatibleCheck()
        >>> check(_item("CC0-1.0")).passed
        True
        >>> r = check(_item("proprietary"))
        >>> r.passed, r.severity
        (False, 'P0')

    Complexity: O(1) — set membership.
    """

    name: str = "license_compatible"
    severity: Literal["P0", "P1"] = "P0"
    permit_local_only: bool = False

    def __call__(self, item: Item) -> QualityCheckResult:
        """Run the check; see class docstring."""
        license_id = item.provenance.license
        if license_compatible(license_id):
            return QualityCheckResult(
                name=self.name, passed=True, severity=self.severity,
                detail=f"license={license_id} on allowlist",
            )
        if self.permit_local_only:
            return QualityCheckResult(
                name=self.name, passed=True, severity="P1",
                detail=f"license={license_id} not on allowlist; flagged for local-only retention",
            )
        return QualityCheckResult(
            name=self.name, passed=False, severity=self.severity,
            detail=f"license={license_id} not in redistribution allowlist",
        )


__all__ = ["LicenseCompatibleCheck"]
