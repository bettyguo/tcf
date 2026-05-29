"""Pre-commit hook: forbid committing corpora under `data/`.

Master prompt §6.3 + Phase 1 §7 I5 + RISK_REGISTER R-006: the `data/`
directory holds operator-supplied corpora and ingested third-party content.
Corpora must never be committed.

The Phase 9 launch added two public sub-trees that are NOT corpora and ARE
committed:

- `data/audit/**`   — Phase 9 audit dossier (planner-simulator JSON,
  calibration plot, security/perf/content/a11y summaries, signed
  evidence files cited by `LAUNCH_READINESS_REPORT.md`).
- `data/calibration/**` — published κ tables + calibrator metadata
  referenced from the README's "Honesty receipts" section (ADR-048).

Everything else under `data/` remains forbidden.

Usage (invoked by pre-commit):
    python scripts/check_no_data_commit.py path/one path/two ...

Exits 1 if any provided path is under `data/` and outside the
allowlisted public sub-trees; 0 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath

# Public, committable sub-trees inside `data/`. Anything else under
# `data/` is treated as corpora and rejected.
_ALLOWED_DATA_SUBDIRS = frozenset({"audit", "calibration", ".gitkeep"})


def main(argv: list[str] | None = None) -> int:
    paths = (argv if argv is not None else sys.argv[1:])
    offenders = []
    for raw in paths:
        # Normalize Windows-style backslashes for the check.
        p = PurePosixPath(raw.replace("\\", "/"))
        parts = p.parts
        if parts and parts[0] == "data" and len(parts) > 1 and parts[1] not in _ALLOWED_DATA_SUBDIRS:
            offenders.append(raw)

    if offenders:
        print("ERROR: refusing to commit corpora files under data/:", file=sys.stderr)
        for o in offenders:
            print(f"  - {o}", file=sys.stderr)
        print(
            "\nThe data/ directory is gitignored except for the public audit +\n"
            "calibration sub-trees. Corpora come from the operator's ingestion\n"
            "pipeline, not from this repo. See master prompt §6.3 and\n"
            "RISK_REGISTER R-006.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
