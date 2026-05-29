# ADR-0038: Publish Cohen's κ with every release; experimental badge below 0.55

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 7 (Auto-Scoring & Feedback)

## Context

The auto-scoring κ — quadratic-weighted Cohen's κ on the 0–5 rubric
dimensions against expert raters — is the load-bearing trust signal
for the EE/EO rubric pipeline. If the κ table is not visible at
release time, an operator can re-tune the calibrator, drift the
metric, and ship a degraded scorer without anyone noticing. We have
seen the failure pattern across the L2 auto-scoring literature.

`phase7_think.md §8.3` requires every release to run
`scripts/eval_kappa.py` against the available expert subset. The
question this ADR settles is: what do we do with κ values below the
target band?

## Decision

1. `scripts/eval_kappa.py` runs on every release as part of the audit
   suite. The κ table is emitted to `data/calibration/<rubric>.kappa.json`
   and embedded in the release notes.
2. The release-time evaluator exits non-zero when overall κ < 0.55
   unless `--allow-experimental` is set explicitly. CI gates the
   release on this exit code.
3. A release whose published overall κ is below 0.55 ships only with
   the "experimental" badge in the in-app rubric surface; the badge
   carries the disclaimer "This scorer's agreement with expert raters
   is below the trustworthy band; treat scores as suggestive only."
4. The κ table MUST include the rater label (`gold` / `silver` per
   ADR-037).

The 0.55 cutoff is well below the 0.65 published-research target
(ADR-036). A release between 0.55 and 0.65 is "below target but in
the trust window"; one below 0.55 is "experimental, ship only with
the badge."

## Consequences

- The release process gains an audit step that verifies the κ table
  exists, is signed by the calibrator's training-set hash, and meets
  the gate.
- The in-app rubric component (Phase 8) renders the experimental
  badge based on the κ JSON's `experimental: true` flag.
- The risk register tracks `R-040 LLM score inflation` as the
  failure mode this ADR contains (via the inflation guard) plus
  `R-046 published κ drift across releases` as the failure mode this
  ADR introduces by making the published κ a release blocker.

## Related

- ADR-036, ADR-037, ADR-040
- `phase7_audit.md §1` (κ on expert held-out)
- `scripts/eval_kappa.py`
