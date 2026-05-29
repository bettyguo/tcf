"""Source modules.

Each source ships as `tcf_accel_content.sources.<name>` and exposes a
class implementing the `Source` protocol. Open-license sources are
imported by `seed_bank.py --open-only`; operator-tier sources live
under `tcf_accel_content.sources.operator.*` and require the operator
to have populated `data/operator/<name>/` first.

The Phase 3 implementation lands the concrete classes; this module
ships only the protocol and the SPDX allowlist.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Protocol, runtime_checkable

from tcf_accel_content.types import RawAsset

# SPDX-style identifiers we accept for items the *repo* may redistribute.
# Operator-tier sources may use other licenses; those items never enter
# the open-only seed bank.
REDISTRIBUTABLE_LICENSE_ALLOWLIST: frozenset[str] = frozenset({
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "PublicDomain",
})


@runtime_checkable
class Source(Protocol):
    """The uniform source-module interface.

    Implementations expose `name`, `license`, and `redistributable`
    as plain attributes (class-level or instance-level — both satisfy
    the protocol) and yield `RawAsset` instances from `iter_assets`.
    """

    name: str
    license: str
    redistributable: bool

    def iter_assets(
        self,
        *,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> Iterator[RawAsset]:
        """Yield `RawAsset` items from this source.

        Args:
            limit: Maximum number of assets to yield (None = no limit).
            since: Yield only assets whose `fetched_at >= since`.
        """
        ...


def license_compatible(license_id: str) -> bool:
    """True iff `license_id` is in the redistribution allowlist.

    Used by the quality gate's P0 license check and by the
    `--open-only` seed mode to filter out operator-tier sources.

    Example:
        >>> license_compatible("CC0-1.0")
        True
        >>> license_compatible("proprietary")
        False

    Complexity: O(1).
    """
    return license_id in REDISTRIBUTABLE_LICENSE_ALLOWLIST


__all__ = [
    "REDISTRIBUTABLE_LICENSE_ALLOWLIST",
    "Source",
    "license_compatible",
]
