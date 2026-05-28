"""Pre-commit hook: forbid committing files under `data/`.

Master prompt §6.3 + Phase 1 §7 I5 + RISK_REGISTER R-006: the `data/`
directory holds operator-supplied corpora and ingested third-party content.
It must never be committed.

Usage (invoked by pre-commit):
    python scripts/check_no_data_commit.py path/one path/two ...

Exits 1 if any provided path is under `data/`; 0 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath


def main(argv: list[str] | None = None) -> int:
    paths = (argv if argv is not None else sys.argv[1:])
    offenders = []
    for raw in paths:
        # Normalize Windows-style backslashes for the check.
        p = PurePosixPath(raw.replace("\\", "/"))
        parts = p.parts
        if parts and parts[0] == "data" and (len(parts) > 1 and parts[1] != ".gitkeep"):
            offenders.append(raw)

    if offenders:
        print("ERROR: refusing to commit files under data/:", file=sys.stderr)
        for o in offenders:
            print(f"  - {o}", file=sys.stderr)
        print(
            "\nThe data/ directory is gitignored on purpose. Corpora come from the\n"
            "operator's ingestion pipeline, not from this repo. See master prompt §6.3\n"
            "and RISK_REGISTER R-006.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
