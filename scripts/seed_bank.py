r"""Phase 3 foundation seed-bank CLI.

Thin wrapper over `tcf_accel_content.seed_bank.main`. Invoke via:

    uv run python scripts/seed_bank.py --mode open-only \
        --target-ce 8 --target-co 4 --target-ee 4 --target-eo 4

See `phase3_design.md §10` for the design and
`tcf_accel_content.seed_bank` for the implementation. Phase 3
follow-up swaps the FakeCEFRClassifier + InMemoryBankWriter for the
production CamemBERT + PostgresBankWriter without changing this
operator-facing surface.
"""

from __future__ import annotations

import sys

from tcf_accel_content.seed_bank import main

if __name__ == "__main__":
    sys.exit(main())
