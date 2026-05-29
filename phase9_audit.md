# Phase 9 — AUDIT

> Evidence dossier for the six audit gates plus the launch
> checklist. Each section names the evidence file under
> `data/audit/phase9/` and summarizes its verdict. The signed
> readiness report (`LAUNCH_READINESS_REPORT.md`) is the
> consolidated decision; this file is the audit narrative.

---

## 1. Pedagogy audit

**Evidence:** `data/audit/phase9/pedagogy_audit.json` +
`data/audit/phase9/pedagogy_calibration.md` + test results from
`pytest -q tests/pedagogy/launch_audit.py`.

**Method:** `tests/pedagogy/launch_audit.py` runs twelve launch
cohorts; for each, 100 stochastic trajectories under the planner's
own allocation, comparing the simulator's median to the planner's
analytic projection.

**Result:** **PASS**. All 12 cohorts clear all three gates
(calibration ±0.5 NCLC, projection-outcome consistency, kind-
specific assertion). Calibration delta is ±0.05 NCLC across all
cohorts — significantly tighter than the 0.5-NCLC window.

**Per-cohort headline:**

| Cohort | kind | planner | simulated median | P(success) | gate |
|---|---|---|---|---|---|
| solid_B1_target_NCLC7 | realistic | 7.10 | 7.15 | 1.00 | ✅ |
| solid_B1_target_NCLC9 | honest_refusal | 7.20 | 7.19 | 0.00 | ✅ |
| uneven_target_NCLC7 | realistic | 7.10 | 7.15 | 1.00 | ✅ |
| strong_B2_target_NCLC9 | realistic | 9.10 | 9.15 | 1.00 | ✅ |
| aggressive_B1_target_C2 | honest_refusal | 7.10 | 7.06 | 0.00 | ✅ |
| short_runway_target_NCLC7 | honest_refusal | 6.10 | 6.10 | 0.00 | ✅ |
| low_budget_target_NCLC7 | honest_refusal | 5.80 | 5.75 | 0.00 | ✅ |
| already_at_target | trivial | 9.80 | 9.78 | 1.00 | ✅ |
| heritage_production_gap | realistic | 7.40 | 7.38 | 1.00 | ✅ |
| reception_only_weakness | realistic | 7.20 | 7.22 | 1.00 | ✅ |
| ee_bottleneck_only | realistic | 8.20 | 8.24 | 1.00 | ✅ |
| eo_bottleneck_only | realistic | 8.20 | 8.23 | 1.00 | ✅ |

**Calibration plot:** `data/audit/phase9/pedagogy_calibration.md`
(Mermaid quadrant chart).

**Honest-refusal pattern verified:** four cohorts where the
planner refused to project success (B1→C2; B1→NCLC9 in 84 days;
short runway; low budget). In every case the simulator agrees
(P(success) = 0.00). The system is not lying in either direction.

---

## 2. Security audit

**Evidence:** `data/audit/phase9/security_audit.md`.

**Method:** Two-maintainer fallback per ADR-047. Both maintainers
ran the full toolchain on a clean checkout (`ruff`, `mypy`,
`bandit`, `pip-audit`, `pnpm audit`, `trivy fs`, `gitleaks`) and
spot-checked the authz-fuzz coverage against the OpenAPI spec.

**Result:** **PASS**. Zero high-severity findings from any
toolchain; OWASP Top 10 control matrix verified; security headers
present on all responses; PII scrubber active and tested.

**Accepted residual exposures (per ADR-046):**

- No third-party external audit at v1.0 (v1.1 commitment).
- ZAP dynamic scan not in CI (k6 perf tests exercise the surface).
- Multi-tenant deployment unsupported (v1.0 is single-tenant by
  design).

Each carries a one-paragraph rationale in
`data/audit/phase9/security_audit.md §Residual exposures`.

---

## 3. Performance audit

**Evidence:** `data/audit/phase9/perf_summary.md` (+ raw k6 JSON
in `perf_sustained.json`, `perf_burst.json`, `perf_cold_start.json`).

**Method:** k6 scripts in `tests/load/k6_*.js` run against the
staging deployment.

**Result:** **PASS**.

- Sustained: p95 = 198 ms (gate < 250 ms); failrate 0.03%
  (gate < 0.1%).
- Burst: 14823 mock starts (gate > 14500); 7 scoring failures
  (gate < 50).
- Cold-start: 41.7 s (gate < 60 s).
- Disk: 17.4 GB seeded bank (gate ≤ 20 GB).
- Lighthouse: all four launch routes ≥ 90 across all four
  categories.

---

## 4. Content audit

**Evidence:** `data/audit/phase9/content_audit.md` +
`content_handreview.md`.

**Method:** distribution check (`scripts/seed_bank.py --audit-only`)
+ 100-items-per-module hand review + 10-CO-items-per-band FEI
drift check + PII/copyright/harm grep.

**Result:** **PASS**. All four sub-audits clean. One minor
B2 CO genre drift noted (under-representation of news/current-
affairs items relative to latest FEI samples); added to v1.1
content backlog. Three items pulled from the bank for re-leveling
in v1.1 (CE: 2, EO: 1) based on hand-review disagreements.

---

## 5. Accessibility audit

**Evidence:** `data/audit/phase9/a11y_conformance.md` +
`think_aloud_notes.md`.

**Method:** Phase 8 toolchain (Lighthouse + pa11y + axe-core)
re-run against staging; WCAG 2.2 AA manual checklist walked by
two maintainers; NVDA + VoiceOver walkthrough of all five drill
types; Deaf-friendly path verified; three-maintainer think-aloud
on the live staging build.

**Result:** **PASS**.

- Lighthouse accessibility: 98–100 on all four launch routes.
- pa11y: zero WCAG 2.2 AA violations.
- axe-core: zero violations in the component library.
- WCAG 2.2 AA manual checklist: all 13 principles + WCAG 2.2
  additions verified by both reviewers.
- Three-maintainer think-aloud: no P0 findings; three small UX
  polish items logged for v1.1.

---

## 6. Documentation audit

**Evidence:** `data/audit/phase9/docs_audit.md` (generated by
`scripts/release/audit_docs.py`).

**Method:** automated grep for `# TODO` / `FIXME` / `XXX` across
all 12 required docs; presence check for each.

**Result:** **PASS**. Every required doc exists; zero TODO/FIXME
markers across the corpus. Each new doc (LIMITATIONS, LEARNER_GUIDE,
PEDAGOGY, ARCHITECTURE, OPERATIONS) was edited by a second
maintainer; signoffs recorded in the per-doc frontmatter (Phase 9
convention).

---

## 7. Risk register

**Evidence:** `data/audit/phase9/risk_register_check.md` + the
"Changes this phase (Phase 9)" subsection in `RISK_REGISTER.md`.

**Method:** every Open risk re-evaluated to Mitigated, Accepted,
or Retired per ADR-046.

**Result:** **OPEN_COUNT = 0**. Twelve risks transitioned to
Mitigated; seven Accepted with explicit two-maintainer-signed
rationales + v1.1 follow-ups; zero remaining Open.

---

## 8. FEI source-of-truth check

**Evidence:** `data/audit/phase9/fei_source_check.md`.

**Method:** re-read the FEI page at the canonical URL; diff the
on-disk `packages/shared/.../schemas/exam_format.py` against the
page's section structure, item counts, durations, and NCLC
mapping table.

**Result:** **verified**. No drift. The rumoured adaptive-listening
29-question variant (R-001) is still not present on the FEI page;
R-001 remains mitigated, not Re-Opened.

---

## 9. κ publication

**Evidence:** `data/audit/phase9/kappa_publication.md` +
`data/calibration/ee.v1.report.md` + README "Honesty receipts"
section.

**Method:** ADR-038 release gate; ADR-048 README publication.

**Result:** **PASS**. EE κ_silver ≥ 0.65 across all six
dimensions; values matched between source-of-truth and README;
training-set hash recorded; experimental badge active.

---

## 10. Release artefacts

**Evidence:** `data/audit/phase9/release_artefacts.md` +
`dist/release/SHA256SUMS` (+ cosign signature).

**Method:** `scripts/release/build_release.py` run by the CI
release workflow on tag.

**Result:** **PASS**. All wheels, Docker images (multi-arch),
Helm chart, SBOM, and SHA-256 manifest built and (where
applicable) signed.

---

## 11. Demo deployment observation

**Evidence:** `data/audit/phase9/demo_observation.md`.

**Method:** demo deployment up for 48 h with synthetic light load
and the alert pipeline wired.

**Result:** **PASS**. Zero P0 alerts across the window. One
planned worker restart at hour 31; cache hit rate dipped to 0.94
then recovered.

---

## 12. Signed Launch Readiness Report

**Evidence:** `LAUNCH_READINESS_REPORT.md` at the repo root.

**Method:** `scripts/release/sign_audit_report.py --strict
--auditor "Jikun <bettydxguo@gmail.com>" --release-tag v1.0.0`.

**Result:** **PASS**. All 12 launch-checklist gates green.
Bundle SHA-256: `9b064a2a3f73c74278a955e937955c9d93b2e35589c95f6213c04f0228a08bb1`.

---

## 13. ADRs added in Phase 9

- ADR-046: Launch criteria are blocking, not advisory.
- ADR-047: External security review for v1.0 (or two-maintainer
  sign-off as a fallback).
- ADR-048: Public publication of κ + cohort-success simulation
  results in the README.

All three accepted at v1.0.0 release.

---

## 14. Hand-off integration (Phase 8 → Phase 9)

The two Phase 8 hand-offs (Phase 8 evaluate §1 rows 3 and 5) were
picked up in Phase 9:

- **Live `/v1/*` wiring** (row 3): the single-file change in
  `app/(app)/today/page.tsx` lands in the v1.0 build. The
  remaining surface (`/insights`, `/drill/[id]`) was wired in the
  same PR; the fixture path was removed.
- **Three-maintainer think-aloud** (row 5): run against the
  staging build on 2026-05-28; results in `a11y_conformance.md §5`.

Both hand-offs verified.

---

## 15. What this audit does *not* verify

To stay honest:

- **Real-learner outcomes vs simulated.** v1.0 is pre-pilot; we
  have no real-learner data to compare. `OPERATIONS.md §10`
  describes the post-launch capture; the comparison lives in
  v1.1.
- **κ_gold against a 200-row expert set.** R-010 + ADR-037 keep
  this Accepted at v1.0 with the experimental badge.
- **External third-party security review.** ADR-047 fallback at
  v1.0; v1.1 commitment.
- **Multi-tenant data isolation surface.** v1.0 is single-tenant;
  v1.1 roadmap §2.

Each of these is explicit in the audit dossier; none is hidden.

---

## 16. Conclusion

Twelve gates green. Bundle hash recorded. Auditor signed. The
v1.0.0 tag is honest about what was verified and what was
deferred; the deferrals are themselves verified to be intentional.

The audit is complete; the verdict lives in `phase9_evaluate.md`.
