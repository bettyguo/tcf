# ADR-0047: External security review for v1.0 (or two-maintainer sign-off as a fallback)

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, DevOps lead
- **Phase**: 9 (Quality Audit, Security, Performance, Content Review & Launch)

## Context

`phase9_design.md §3` names the security controls (OWASP Top 10
coverage), the toolchain (`pip-audit`, `npm audit`, `trivy`,
`gitleaks`, `bandit`), and the authz-fuzz test
(`tests/integration/test_authz_fuzz.py`). That covers static,
dependency, secrets, and authorization-coverage testing.

It does *not* cover an adversarial review by someone who didn't
write the code. An external pentest of an OSS project is rarely
budgeted; we cannot promise it. We need a clear policy that
describes what v1.0 does ship, so that the launch claim is honest.

The risk we're managing: shipping a v1.0 with a "security
verified" claim that rests on the maintainers' own toolchain runs.
Without a second pair of eyes, blind spots in the threat model
go unexamined.

## Decision

v1.0 ships with **one of**:

1. **Preferred:** an external WCAG + security audit signed off by
   a third party, with the audit report committed to
   `data/audit/phase9/external_review.pdf` and referenced from
   `LAUNCH_READINESS_REPORT.md`. OR
2. **Fallback:** a two-maintainer independent review documented in
   `data/audit/phase9/sec_review_internal.md`. Each maintainer:
   - Runs the security toolchain (`make security-scan`) on a
     clean checkout.
   - Spot-checks the authz-fuzz test's route coverage against the
     OpenAPI spec (`docs/api/openapi.v1.yaml`).
   - Reads the security headers middleware and the PII scrubber
     end-to-end.
   - Signs the document with their identity and the date.

v1.1 commits to acquiring (1) if any budget is available. The
fallback is the realistic v1.0 path; we say so in the launch
post.

## Consequences

- v1.0 honestly says "two-maintainer fallback" in the launch
  post and in `SECURITY.md`. Readers who require a third-party
  audit can wait for v1.1.
- The fallback is documented and reproducible — the script that
  the two maintainers run is committed (`make security-scan`),
  not bespoke per-maintainer.
- The fallback has known limits: two maintainers from the same
  team share blind spots an adversarial reviewer would not. We
  accept this for v1.0 and commit to closing the gap in v1.1.
- If a CVE drops on a dependency post-v1.0, the patch policy in
  `SECURITY.md` applies; the launch ADR does not need updating
  for each patch.

## Alternatives considered

1. **Block the launch on external audit.** Rejected: budget is
   not guaranteed and we have shipped the launch readiness
   discipline; refusing to ship the discipline because the audit
   is missing would be perverse.
2. **Skip the review entirely.** Rejected: an unaudited claim is
   no claim.
3. **Single-maintainer self-review.** Rejected: one person's
   blind spots are not the project's threat model.

## Related

- ADR-0046 (launch criteria are blocking)
- ADR-0017 (privacy default: local_only)
- `SECURITY.md` — disclosure policy
- `phase9_design.md §3` — security control matrix
- `data/audit/phase9/security_audit.md` — the running record
- `tests/integration/test_authz_fuzz.py` — the authz fuzzer
