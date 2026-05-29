# ADR-0037: Expert-labelled set (≥ 200 / skill) is launch-blocking for "claimed κ"

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 7 (Auto-Scoring & Feedback)

## Context

The published κ on the EE and EO scorers is the central trust signal
for the auto-scoring surface. A κ measured on synthetic or
LLM-as-rater data alone is a category mistake — it certifies
agreement-with-the-LLM, not agreement-with-experts. The system must
not blur the distinction.

`07_AUTO_SCORING_AND_FEEDBACK.md §1.6` and `phase7_think.md §9`
describe three acquisition paths:

1. Partner Alliance Française or DELF/TCF examiners — gold-standard
   reference set.
2. Crowd-sourced learners on the project's mailing list (with consent
   and a license to use the ratings for training).
3. LLM ensemble as a silver-label stand-in, deflated against a
   smaller (~30 essay) actual-expert subset.

## Decision

For each rubric version we deploy:

- The system MUST publish a κ table on each release.
- The κ table MUST be labelled `gold` or `silver` based on the rater
  set.
- A "claimed κ" (the value featured in marketing copy, the in-app
  rubric tooltip, or operator-facing reports without qualification)
  requires `gold` rater data with ≥ 200 EE submissions and ≥ 200 EO
  recordings, each rated by at least 2 expert raters.
- Until that threshold is met the system reports `κ_silver` and the
  release tag carries the "experimental" suffix; the in-app rubric
  surface shows the experimental badge defined in ADR-038.

The threshold is a hard release gate for the "claimed κ" phrase, not
for shipping. We ship calibrated-on-silver scorers — but we never
claim gold-grade agreement we cannot defend.

## Consequences

- The "experimental" badge is wired into the SubmissionView rubric UI
  per release.
- A release whose calibrator was fit on silver labels MUST include
  the rater-set tag in the calibrator JSON
  (`reports[].rater_label`) and the audit verifies it.
- The Phase 7 evaluate doc lists this as an anti-criterion: shipping
  "claimed κ" without ≥ 200 gold-rated labels is a launch-blocker
  for that release.

## Related

- ADR-036 (hybrid architecture)
- ADR-038 (publish κ with every release)
- `phase7_think.md §9`
- `phase7_design.md §10`
