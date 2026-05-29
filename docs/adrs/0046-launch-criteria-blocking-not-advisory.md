# ADR-0046: Launch criteria are blocking, not advisory

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect, DevOps lead
- **Phase**: 9 (Quality Audit, Security, Performance, Content Review & Launch)

## Context

`phase9_design.md §8` enumerates a twelve-item launch checklist:
pedagogy audit, security audit, performance audit, content audit,
accessibility audit, documentation audit, risk-register clean,
FEI source check, κ publication, release artefacts, demo
observation, signed readiness report.

Without a binding rule, a maintainer could rationalise shipping
with a yellow gate ("we'll fix it in 1.0.1"). Six months in,
"yellow" becomes the cultural default and the launch discipline
erodes. We have already seen this pattern in OSS projects we
respect.

The user's framing of Phase 9 is unambiguous: *"in the end all
functions are in ready-to-launch state."* A yellow gate is
not ready to launch.

## Decision

**Every item on the launch checklist is blocking.**

- A red checkbox blocks the `v1.0.0` tag.
- A yellow checkbox requires an explicit Accepted-risk entry in
  `RISK_REGISTER.md` and a one-paragraph rationale signed by two
  maintainers. Without that entry and signature, a yellow item
  is treated as red.
- There is no "we'll fix it in 1.0.1" path: if it isn't in 1.0,
  it isn't in 1.0. A v1.0.1 patch release fixes bugs we shipped,
  not gates we deferred.

The signing script (`scripts/release/sign_audit_report.py`)
exits non-zero under `--strict` whenever any required gate is
not green. The CI release workflow runs the signer with
`--strict`; the tag job depends on the signer succeeding.

The launch checklist itself (`scripts/release/launch_checklist.yaml`)
is the executable record. Changes to the checklist require a PR
that updates this ADR's "Consequences" section with the rationale
for the change.

## Consequences

- The path to the `v1.0.0` tag is slower. We accept this.
- The tag, when it lands, is honest about what was verified. We
  accept the trade.
- A v1.0.1 cannot retroactively "fix" a gate that didn't pass at
  v1.0; if a gate was deferred, the deferral lives in the risk
  register and the consequence is visible.
- Future phases that propose new gates must either (a) extend
  this ADR with the same blocking semantics, or (b) write a
  superseding ADR that explicitly relaxes the rule (and explains
  why).

## Alternatives considered

1. **Advisory checklist with maintainer judgment.** Rejected:
   we have evidence (from adjacent OSS projects) that advisory
   gates erode within ~6 months.
2. **Blocking only for "high-severity" items.** Rejected:
   severity classification is itself a judgment call and would
   move the erosion problem one level up.
3. **External release-engineer veto.** Considered for v1.1; the
   release-engineer role does not exist at v1.0 (single-
   maintainer reality).

## Related

- ADR-0047 (external security review for v1.0 / fallback)
- ADR-0048 (public publication of κ + cohort results)
- `scripts/release/launch_checklist.yaml` — the executable form
- `scripts/release/sign_audit_report.py` — the gate runner
- `phase9_design.md §8, §11`
- `phase9_evaluate.md`
