---
layout: default
title: tcf-accel
description: "Open-source, evidence-based French training for the TCF Canada. B1 → NCLC 7–9 in 12 weeks. Honesty receipts inside."
---

# tcf-accel

> An open-source, evidence-based, exam-aligned French training system for
> candidates moving from CEFR **B1 → NCLC 7–9** on the **TCF Canada** in
> 12 weeks.

**Status:** [v1.0.0](LAUNCH_READINESS_REPORT.md) — launched 2026-05-28.
All 12 launch-checklist gates green. Signed Launch Readiness Report
committed.

> **Read this first:** [LIMITATIONS.md](LIMITATIONS.md). It tells you what
> the system does *not* do. If anything there is a deal-breaker, choose
> another path. That is by design.

---

## For learners

If you're a candidate considering this system for your TCF Canada prep:

1. Read [LIMITATIONS.md](LIMITATIONS.md). Don't skip this.
2. Read the [Learner Guide](LEARNER_GUIDE.md) — the 12-week journey,
   week by week.
3. The system is self-hosted; see [OPERATIONS.md](OPERATIONS.md) or
   ask your operator to stand it up.

## For operators

If you're standing this up for yourself or a small group:

- [README.md](README.md) — 5-minute setup.
- [OPERATIONS.md](OPERATIONS.md) — runbooks: env vars, JWT rotation,
  backups, security headers, queue health, schedule-cache alarms,
  real-learner trajectory capture, cost of operation, incident
  response.
- [Architecture overview](ARCHITECTURE.md) — eight surfaces, ADR
  index, deployment posture.

## For reviewers

If you're here to grade our claims:

- [Honesty receipts (κ + cohort tables)](README.md#honesty-receipts)
- [Launch Readiness Report](LAUNCH_READINESS_REPORT.md) — the signed
  v1.0.0 launch decision (bundle SHA-256 inside).
- [Pedagogy dossier](PEDAGOGY.md) — eight SLA principles tied to code +
  tests + ADRs.
- [Risk register](RISK_REGISTER.md) — zero Open at v1.0; every Accepted
  risk carries a two-maintainer-signed rationale (per ADR-046).

## For contributors

- [CONTRIBUTING.md](CONTRIBUTING.md) — dev loop, branching, PR
  checklist.
- [v1.1 roadmap](docs/roadmap/v1.1.md) — the "what's missing" list,
  pre-empted.
- [Architecture Decision Records](docs/adrs/) — 48 ADRs covering every
  load-bearing design decision.

---

## Phase 9 audit artefacts

These are the evidence files the [signed readiness
report](LAUNCH_READINESS_REPORT.md) hashes:

| Audit | Result | Evidence |
|---|---|---|
| Pedagogy (12 cohorts × 100 trajectories) | ✅ | [pedagogy_audit.json](data/audit/phase9/pedagogy_audit.json) + [calibration plot](data/audit/phase9/pedagogy_calibration.md) |
| Security (OWASP Top 10 + toolchain) | ✅ | [security_audit.md](data/audit/phase9/security_audit.md) |
| Performance (sustained / burst / cold-start) | ✅ | [perf_summary.md](data/audit/phase9/perf_summary.md) |
| Content (distribution + hand-review + FEI drift) | ✅ | [content_audit.md](data/audit/phase9/content_audit.md) |
| Accessibility (WCAG 2.2 AA + think-aloud) | ✅ | [a11y_conformance.md](data/audit/phase9/a11y_conformance.md) |
| Documentation (presence + no unfinished markers) | ✅ | [docs_audit.md](data/audit/phase9/docs_audit.md) |
| Risk register (zero Open) | ✅ | [risk_register_check.md](data/audit/phase9/risk_register_check.md) |
| FEI source-of-truth | ✅ | [fei_source_check.md](data/audit/phase9/fei_source_check.md) |
| κ publication | ✅ | [kappa_publication.md](data/audit/phase9/kappa_publication.md) + [EE κ report](data/calibration/ee.v1.report.md) |
| Release artefacts (wheels, Docker, Helm, SBOM) | ✅ | [release_artefacts.md](data/audit/phase9/release_artefacts.md) |
| Demo deploy 48-h observation | ✅ | [demo_observation.md](data/audit/phase9/demo_observation.md) |
| Prior phases (1–8) | ✅ | [prior_phases_passed.md](data/audit/phase9/prior_phases_passed.md) |

---

## What this site is

A read-only docs + receipts site for tcf-accel v1.0.0. The text is
the same text in the repo — published here so a reader doesn't need
to clone to verify our claims.

## What this site is NOT

The running application. The FastAPI backend, Celery worker,
Postgres, Redis, and Next.js web app **cannot** run on GitHub Pages
(static-only). To run the live system, self-host per
[OPERATIONS.md](OPERATIONS.md).

If you want a live hosted demo, the supported paths at v1.0 are
self-hosted Docker Compose or the Helm chart (`infra/helm/`); a
managed-hosting option is on the v1.1 roadmap.

---

## License

- Software: **MIT** ([LICENSE](LICENSE)).
- Content: **CC BY-SA 4.0** ([CONTENT_LICENSE](CONTENT_LICENSE)).

See ADR-0010 for the dual-licensing rationale.
