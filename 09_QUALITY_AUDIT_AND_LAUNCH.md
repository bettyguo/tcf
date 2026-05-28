# PHASE 9 — Quality Audit, Security, Performance, Content Review & Launch

> Goal: a ship-ready system, audited end-to-end against pedagogy, security, performance, accessibility, and content quality. Produces a signed "Launch Readiness Report" and a versioned `v1.0.0` release.

This is the gate the user requested: "in the end all functions are in ready-to-launch state."

---

## 1. THINK (produce `phase9_think.md`)

### 1.1 What "Launch-Ready" Actually Means

A reviewer-grade definition:

1. **Pedagogically valid**: a learner following the system as designed has a *realistic* expectation of moving B1 → NCLC 7–9 in 12 weeks at 2.5 h/day. Backed by the synthetic-cohort simulator and (where possible) early human pilot data.
2. **Safe**: no learner harm from over-predicted NCLC, no copyright risk, no privacy leak, no security hole at the OWASP Top 10 level.
3. **Operable**: a self-hoster can stand up the full stack in one command on a clean machine and a non-technical learner can use it without instruction.
4. **Honest**: every claim made by the marketing copy, the documentation, and the in-app messaging is supported by the data the system collects.
5. **Maintainable**: a new contributor can navigate the codebase using only the docs.
6. **Documented**: a learner can read the FAQ and understand what the system is, what it isn't, and why.

### 1.2 The Three Audits Hardest to Pass

1. **Pedagogy audit**: do the 12 synthetic-cohort trajectories under the system's plan actually converge on the target NCLC distribution? Or is the system optimistic? Without this honest check, everything else is theater.
2. **Calibration audit**: does the κ on the held-out expert set hold up over time, across new prompts, across writing-vs-speaking? Or has the system silently regressed?
3. **Content audit**: is the bank's CEFR-level labeling consistent with current FEI sample materials? Or has drift accumulated?

These three are the launch-blockers if any of them slip.

### 1.3 What We Don't Promise

Be explicit. The system does NOT:

- Guarantee a score.
- Replace a human tutor for high-anxiety candidates or those with significant production gaps.
- Score perfectly — the κ ≤ 0.75 means ~25% of subscale judgments still differ from expert raters by ≥ 1 point.
- Provide CO accessibility for Deaf candidates beyond CE/EE/EO routing.
- Substitute for booking actual practice with native speakers (HelloTalk, Tandem, italki — all linked from the Library).

This honesty is documented in `LIMITATIONS.md`, surfaced in the onboarding, and re-surfaced in the readiness widget.

---

## 2. DESIGN (produce `phase9_design.md`)

### 2.1 The Pedagogy Audit

Run the synthetic-cohort simulator from Phase 4 with realistic noise:

```python
# tests/pedagogy/launch_audit.py
SCENARIOS = [
    Cohort("solid_B1_target_NCLC7", initial=NCLC5_flat, target=7, days=84, daily_min=150),
    Cohort("solid_B1_target_NCLC9", initial=NCLC5_flat, target=9, days=84, daily_min=150),
    Cohort("uneven_target_NCLC7", initial=NCLC{CO:6,CE:6,EE:4,EO:4}, target=7, days=84, daily_min=150),
    Cohort("strong_B2_target_NCLC9", initial=NCLC7_flat, target=9, days=84, daily_min=150),
    Cohort("aggressive_B1_target_C2", initial=NCLC5_flat, target=11, days=84, daily_min=150),  # expected to fail honestly
    Cohort("short_runway_target_NCLC7", initial=NCLC5_flat, target=7, days=42, daily_min=150),
    Cohort("low_budget_target_NCLC7", initial=NCLC5_flat, target=7, days=84, daily_min=60),
    # … 12 cohorts total
]
```

For each: simulate 100 trajectories with stochastic learning + plan execution. Report:

- P(min_skill ≥ target_NCLC at exam_date)
- Per-skill final-day posterior distribution
- Comparison: planner-projected trajectory vs simulated reality (calibration plot)

**Launch gate:** for the realistic cohorts (everything except the "aggressive_B1_target_C2" cohort), the simulated P(success) must match the planner's projection within ±10 percentage points. The aggressive cohort is allowed to fail; the system must have *honestly refused* to promise success in that case.

### 2.2 The Security Audit

- **OWASP Top 10:** verified by manual + automated review (e.g., ZAP scan).
- **Authentication:** JWT with short-lived access + refresh; refresh token rotation; CSRF for cookie-based fallback.
- **Authorization:** every endpoint enforces user-scoped data access; tested with a "second user" fuzz against every `/v1/.../{id}`.
- **Input validation:** Pydantic at all boundaries; explicit limits on uploaded file sizes (audio ≤ 10 MB, text ≤ 50 KB).
- **Secrets:** none in code; `.env.example` with placeholders; `gitleaks` in CI.
- **Dependencies:** `pip-audit`, `npm audit`, `trivy fs`; weekly Renovate-style PRs for security updates.
- **PII:** the bank, the model, and the logs scanned for accidental PII.
- **Logging hygiene:** no learner text or audio in logs or traces.
- **Headers:** HSTS, CSP, X-Frame-Options, Permissions-Policy, all set; verified via `securityheaders.com` or equivalent.

### 2.3 Performance Audit

- Sustained load test (k6): 100 concurrent learners, mixed drill workload, p95 API latency ≤ 250 ms, error rate < 0.1%.
- Burst test: 500 concurrent mock-exam starts (worst case: a tutor cohort), no failed scoring jobs over 30 minutes.
- Cold start: API + worker + DB containers up and healthy in < 60 s from `docker compose up`.
- Disk: full seeded bank fits in ≤ 20 GB.

### 2.4 Content Audit

- Re-run the Phase 3 distribution check. Bank composition must match the quota matrix.
- Sample 100 items per module by hand; verify CEFR labels, correctness of MCQ keys, accessibility of audio.
- Compare a sample of our CO items against published FEI samples; flag drift in difficulty/style/genre coverage.
- Verify no item references PII, copyrighted news content beyond fair-use snippet, or potentially harmful subject matter.

### 2.5 Accessibility Audit (Beyond Phase 8)

- Full WCAG 2.2 AA compliance certified by an external auditor or, lacking budget, two independent maintainers using the WCAG checklist.
- "Deaf-friendly path" documented: a candidate using only CE/EE/EO must be able to follow the planner, run mocks (with CO skipped), and reach the booking decision.

### 2.6 Documentation Audit

The following must exist, be current, and have been edited by someone other than the writer:

- `README.md` (5-minute setup; what it is, what it isn't)
- `LIMITATIONS.md` (the honest "we don't promise this" page)
- `PEDAGOGY.md` (the SLA evidence dossier)
- `ARCHITECTURE.md` (rolled-up from ADRs)
- `OPERATIONS.md` (runbooks for the operator)
- `LEARNER_GUIDE.md` (the 12-week journey, what to expect each week)
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- `LICENSE` + `CONTENT_LICENSE`
- `SECURITY.md` (disclosure policy)

### 2.7 Launch Checklist (must be 100% green)

- [ ] All previous phase gates passed; signed-off
- [ ] Pedagogy audit pass
- [ ] Security audit pass
- [ ] Performance audit pass
- [ ] Content audit pass
- [ ] Accessibility audit pass
- [ ] Documentation audit pass
- [ ] Risk register: every Open risk has a Mitigated or Accepted disposition
- [ ] FEI source-of-truth check: re-verify §1.1 of master prompt against current FEI page
- [ ] `v1.0.0` tag created; Docker images published; Helm chart published
- [ ] Demo deployment running and observed for 48h with no P0 alerts
- [ ] Signed Launch Readiness Report (one page; auditor name + date)

### 2.8 The Post-Launch Roadmap (Reviewer-Anticipating)

The reviewer will ask: "what's missing in v1.0?" Pre-empt with a written v1.1 plan:

- Native mobile (Tauri + iOS via Capacitor).
- A "tutor mode" multi-tenant deployment for Alliance Française / language schools.
- TEF Canada parallel track (similar structure, different exam).
- DELF/DALF support.
- Online-cohort feature (study groups, opt-in, anonymous).
- Improved calibration: target κ ≥ 0.75 with a larger expert set.
- Better Canadian-context coverage: partner with a Québec educator to expand.
- A1–B1 onboarding for candidates starting below B1.

### 2.9 ADRs

- ADR-046: Launch criteria are blocking, not advisory.
- ADR-047: External security review for v1.0 (or two-maintainer-sign-off as a fallback).
- ADR-048: Public publication of κ + cohort-success simulation results in the README.

---

## 3. CODE

- `tests/pedagogy/launch_audit.py` (the synthetic-cohort harness).
- `tests/load/k6_*.js` (load + burst tests).
- `scripts/release/build_release.py` (Docker + Helm + binary builds).
- `scripts/release/sign_audit_report.py` (produces the signed YAML).
- `LIMITATIONS.md`, `LEARNER_GUIDE.md`, etc.
- The README rewrite: "What it is, what it isn't, who built it, how to use it, how to host it."

---

## 4. AUDIT (produce `phase9_audit.md`)

Run all of §2.1–2.6, document outcomes. Specifically:

- Pedagogy audit pass: yes/no per cohort, with the calibration plot.
- Security: ZAP report attached + Bandit/pip-audit/npm-audit/trivy all clean.
- Performance: k6 reports attached + thresholds met.
- Content: distribution report + 100-item hand-review log.
- Accessibility: axe-core + manual walkthroughs documented.
- Documentation: each doc reviewed by a second maintainer; signoff recorded.
- Demo deploy: 48-h observation report attached.

---

## 5. EVALUATE (produce `phase9_evaluate.md`)

Acceptance criteria:

- ✅ Launch checklist 100% green.
- ✅ Pedagogy P(success) for realistic cohorts ≥ 0.65 at target NCLC (the system's own simulated efficacy).
- ✅ Published κ ≥ 0.65 on EE and EO.
- ✅ Security review clean.
- ✅ Lighthouse scores ≥ 90 in all categories.
- ✅ ADRs ADR-046 through ADR-048 accepted.
- ✅ Signed Launch Readiness Report committed to the repo.
- ✅ `v1.0.0` tag exists; release notes drafted.

Anti-criteria:

- ❌ Any single audit item failing without an Accepted-risk justification.
- ❌ Any documentation page with `# TODO` markers.
- ❌ Any synthetic-cohort whose actual P(success) deviates from the planner's projected P(success) by > 15 percentage points.
- ❌ Any "Pass guaranteed" copy anywhere in the product.
- ❌ A "What's missing" list of major features without a corresponding v1.1 roadmap entry.

Hand-off: the Launch Readiness Report (one PDF or signed Markdown), the `v1.0.0` tag, the deployed demo URL, the public κ + cohort report. Announce to the OSS community responsibly: link to LIMITATIONS.md in the launch post.

---

## 6. After Launch

Operate the system. Track:

- Real-learner posterior trajectories vs simulated.
- Bug reports tagged by phase to inform v1.1 prioritization.
- κ drift as new prompts are added (quarterly recalibration).
- FEI format changes (subscribe to FEI announcements).

The work doesn't end at launch; this prompt closes the build phase. The next document (`10_OPERATIONS.md`, not authored in this build) will live with the operator.
