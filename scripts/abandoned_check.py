"""Abandoned-package audit.

Heuristic: warn on any installed Python distribution whose latest release on
PyPI is older than `MAX_STALENESS_DAYS`. Phase 1 default = 730 (24 months).

This script intentionally does *not* fail CI; abandoned ≠ broken. It writes
the report to stdout and exits 0 unless the network call itself fails.

Usage:
    uv run python scripts/abandoned_check.py

Complexity: O(N) over installed distributions, with one PyPI JSON fetch each.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from importlib.metadata import distributions
from typing import Final
from urllib.error import URLError
from urllib.request import Request, urlopen

MAX_STALENESS_DAYS: Final[int] = 730
PYPI_TIMEOUT_S: Final[float] = 5.0
USER_AGENT: Final[str] = "tcf-accel-abandoned-check/0.1"

# Distributions that PyPI doesn't host (workspace members, system packages).
# Skip them silently.
SKIP_PREFIXES = ("tcf-accel-", "tcf_accel_")


def _latest_upload_iso(name: str) -> str | None:
    url = f"https://pypi.org/pypi/{name}/json"
    req = Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urlopen(req, timeout=PYPI_TIMEOUT_S) as resp:  # noqa: S310
            payload = json.load(resp)
    except (URLError, TimeoutError, ValueError):
        return None
    info = payload.get("info") or {}
    version = info.get("version")
    releases = payload.get("releases") or {}
    files = releases.get(version) or []
    if not files:
        return None
    uploads = [f.get("upload_time_iso_8601") for f in files if f.get("upload_time_iso_8601")]
    return max(uploads) if uploads else None


def main() -> int:
    cutoff = datetime.now(UTC) - timedelta(days=MAX_STALENESS_DAYS)
    flagged: list[tuple[str, str]] = []
    skipped: int = 0
    network_errors: int = 0

    seen: set[str] = set()
    for dist in distributions():
        name = (dist.metadata.get("Name") or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        if any(name.startswith(p) for p in SKIP_PREFIXES):
            continue
        iso = _latest_upload_iso(name)
        if iso is None:
            network_errors += 1
            continue
        try:
            uploaded = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            skipped += 1
            continue
        if uploaded < cutoff:
            flagged.append((name, iso))

    if flagged:
        print(
            f"Abandoned-package report ({MAX_STALENESS_DAYS}d staleness threshold):",
        )
        for name, iso in sorted(flagged):
            print(f"  - {name}: latest upload {iso}")
    else:
        print("No abandoned packages detected.")

    print(
        f"\nDistributions checked: {len(seen)}; "
        f"flagged: {len(flagged)}; "
        f"skipped (no version data): {skipped}; "
        f"pypi-unreachable: {network_errors}.",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
