# ADR-0048: Public publication of κ + cohort-success simulation results in the README

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect, ML lead
- **Phase**: 9 (Quality Audit, Security, Performance, Content Review & Launch)

## Context

ADR-0038 (Phase 7) made the published κ a release gate. It said
*what* must be published but not *where*. ADR-0037 distinguishes
κ_silver (against an LLM rater) from κ_gold (against a small
expert set). The README is the first surface a reader sees.

Two credibility signals deserve to be visible in 30 seconds:

1. **Auto-scoring quality** — the published κ table.
2. **Pedagogy claim quality** — the synthetic-cohort P(success)
   table from the Phase 9 launch audit.

A reader who has to clone the repo + dig through `data/audit/` to
find either is a reader we have failed. The README is the right
surface for both.

## Decision

The README contains a `## Honesty receipts` section, linked from
the badge row at the top. The section contains, at minimum:

1. **κ table** (one row per scored dimension, columns: rater kind,
   κ, n, dataset hash). Re-generated from
   `data/calibration/ee.v1.report.md` (and the EO equivalent
   when shipped) on every release.

2. **Cohort table** (one row per launch cohort, columns: cohort
   id, kind, target NCLC, planner projection, simulated median,
   simulated P(success)). Re-generated from
   `data/audit/phase9/pedagogy_audit.json` on every release.

3. **Experimental badge note** until κ_gold ≥ 0.75 on a 200-row
   expert set (R-010 + ADR-037). The note links to
   `LIMITATIONS.md §4`.

The release script (`scripts/release/sign_audit_report.py`)
accepts a `--update-readme-receipts` flag that:

- Reads the two source files.
- Renders the tables.
- Replaces the contents between `<!-- HONESTY-RECEIPTS:START -->`
  and `<!-- HONESTY-RECEIPTS:END -->` markers in the README.
- Fails (exit non-zero) if the markers are missing.

The markers are committed at v1.0.0; future releases regenerate
the contents between them but never edit the surrounding text by
hand.

## Consequences

- README grows by ~30 lines. We accept the verbosity.
- The numbers visible at the top of the repo *always* match the
  audit bundle. A reader can verify our honesty without
  cloning.
- A future release that regresses κ or P(success) immediately
  visible at the top of the README; this acts as a soft pressure
  against silent regressions on top of the hard release gate in
  ADR-0038.
- The "Honesty receipts" framing — borrowed from the OSS
  community's recent practice — is itself a signal: we want
  reviewers to grade us on the receipts, not the marketing
  copy.

## Alternatives considered

1. **Publish only in `PEDAGOGY.md`.** Rejected: the README is the
   first surface; honest projects put honest claims at the top.
2. **Publish only in `LIMITATIONS.md`.** Rejected: that's the
   "what we don't do" page; the receipts deserve a positive
   surface too.
3. **Publish on a separate `HONESTY.md` page.** Rejected: an
   extra page is an extra click; the README is already the
   default surface.

## Related

- ADR-0037 (κ_silver vs κ_gold)
- ADR-0038 (publish κ every release)
- ADR-0046 (launch criteria are blocking)
- R-010 (κ ≥ 0.65 launch-blocking, R-046 κ drift)
- `LIMITATIONS.md §4` — the long-form κ honesty page
- `PEDAGOGY.md §7` — the pedagogy audit description
- `scripts/release/sign_audit_report.py --update-readme-receipts`
