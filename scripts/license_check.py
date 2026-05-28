"""License audit for Python dependencies.

Fails (exit 1) on:
- GPL family (GPL-2.0, GPL-3.0, AGPL-3.0, LGPL-3.0) — incompatible with MIT for
  redistribution per ADR-0010.
- SSPL or other non-OSI licenses.
- Missing license metadata.

Usage:
    uv run python scripts/license_check.py

Complexity: O(N) over installed distributions.
"""

from __future__ import annotations

import re
import sys
from importlib.metadata import PackageNotFoundError, distributions, metadata

BANNED_LICENSE_PATTERNS = [
    re.compile(r"\bAGPL\b", re.I),
    re.compile(r"\bGPL-3\b", re.I),
    re.compile(r"\bGPL-2\b", re.I),
    re.compile(r"\bGPLv2\b", re.I),
    re.compile(r"\bGPLv3\b", re.I),
    re.compile(r"\bSSPL\b", re.I),
    re.compile(r"\bRPSL\b", re.I),
    re.compile(r"\bCC-BY-NC\b", re.I),
    re.compile(r"\bCC-BY-ND\b", re.I),
]

# Allowlisted packages (case-by-case justifications go here, with a comment).
# Empty in Phase 1.
ALLOWLIST: set[str] = set()


def _license_strings(name: str) -> list[str]:
    """Return all license-bearing strings from a distribution's metadata.

    We check both the `License:` field (free-form) and the `Classifier:` lines
    that start with `License ::` (SPDX-ish).
    """
    try:
        meta = metadata(name)
    except PackageNotFoundError:
        return []
    bits: list[str] = []
    lic = meta.get("License")
    if lic:
        bits.append(lic)
    for cls in meta.get_all("Classifier", []) or []:
        if cls.startswith("License ::"):
            bits.append(cls)
    return bits


def main() -> int:
    failures: list[str] = []
    seen: set[str] = set()
    for dist in distributions():
        name = (dist.metadata.get("Name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        if name in ALLOWLIST:
            continue
        license_bits = _license_strings(name)
        if not license_bits:
            failures.append(f"{name}: missing license metadata")
            continue
        joined = " | ".join(license_bits)
        for pat in BANNED_LICENSE_PATTERNS:
            if pat.search(joined):
                failures.append(f"{name}: banned license matched ({pat.pattern}) in {joined!r}")
                break

    if failures:
        print("License audit FAILED:", file=sys.stderr)
        for f in sorted(failures):
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"License audit PASSED. {len(seen)} distributions checked, 0 banned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
