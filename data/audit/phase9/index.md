---
layout: default
title: "Phase 9 audit dossier"
eyebrow: "Evidence files"
subtitle: "The 13 evidence files the signed LAUNCH_READINESS_REPORT hashes. Each file is a checkable artefact — no narrative, just the structured outputs of the launch gates."
permalink: /data/audit/phase9/
---

The signed [Launch Readiness Report]({{ '/LAUNCH_READINESS_REPORT/' | relative_url }}) takes a SHA-256 over every file under this directory at signing time. The bundle hash is `9b064a2a3f73c74278a955e937955c9d93b2e35589c95f6213c04f0228a08bb1`; if any file below is modified, that hash will change.

## Gate evidence

<ul class="adr-list">
  <li><span class="num">P9-01</span><a class="title" href="{{ '/data/audit/phase9/prior_phases_passed/' | relative_url }}">Prior phase gates passed (Phase 1–8 walk)</a></li>
  <li><span class="num">P9-02</span><a class="title" href="{{ '/data/audit/phase9/pedagogy_audit.json' | relative_url }}">Pedagogy audit JSON — 12 cohorts × 100 trajectories</a></li>
  <li><span class="num">P9-02</span><a class="title" href="{{ '/data/audit/phase9/pedagogy_calibration/' | relative_url }}">Pedagogy calibration plot + per-cohort table</a></li>
  <li><span class="num">P9-03</span><a class="title" href="{{ '/data/audit/phase9/security_audit/' | relative_url }}">Security audit — OWASP Top 10 controls + toolchain</a></li>
  <li><span class="num">P9-04</span><a class="title" href="{{ '/data/audit/phase9/perf_summary/' | relative_url }}">Performance audit — sustained / burst / cold-start</a></li>
  <li><span class="num">P9-05</span><a class="title" href="{{ '/data/audit/phase9/content_audit/' | relative_url }}">Content audit — distribution + hand-review + FEI drift</a></li>
  <li><span class="num">P9-06</span><a class="title" href="{{ '/data/audit/phase9/a11y_conformance/' | relative_url }}">Accessibility — WCAG 2.2 AA + screen reader + think-aloud</a></li>
  <li><span class="num">P9-07</span><a class="title" href="{{ '/data/audit/phase9/docs_audit/' | relative_url }}">Documentation audit — no unfinished markers</a></li>
  <li><span class="num">P9-08</span><a class="title" href="{{ '/data/audit/phase9/risk_register_check/' | relative_url }}">Risk register check — zero Open</a></li>
  <li><span class="num">P9-09</span><a class="title" href="{{ '/data/audit/phase9/fei_source_check/' | relative_url }}">FEI source-of-truth re-verification</a></li>
  <li><span class="num">P9-10</span><a class="title" href="{{ '/data/audit/phase9/kappa_publication/' | relative_url }}">κ publication check (against ee.v1)</a></li>
  <li><span class="num">P9-11</span><a class="title" href="{{ '/data/audit/phase9/release_artefacts/' | relative_url }}">Release artefacts — wheels, Docker, Helm, SBOM</a></li>
  <li><span class="num">P9-12</span><a class="title" href="{{ '/data/audit/phase9/demo_observation/' | relative_url }}">Demo deployment 48-h observation</a></li>
</ul>

## Source files

- Pedagogy audit raw JSON: <a href="{{ '/data/audit/phase9/pedagogy_audit.json' | relative_url }}"><code>pedagogy_audit.json</code></a>
- Published κ report (EE rubric): <a href="{{ '/data/calibration/ee.v1.report/' | relative_url }}"><code>data/calibration/ee.v1.report</code></a>
- The signed report itself: <a href="{{ '/LAUNCH_READINESS_REPORT/' | relative_url }}">LAUNCH_READINESS_REPORT</a>
- The audit narrative: <a href="https://github.com/bettyguo/tcf/blob/main/phase9_audit.md">phase9_audit.md ↗</a>
- The verdict: <a href="https://github.com/bettyguo/tcf/blob/main/phase9_evaluate.md">phase9_evaluate.md ↗</a>
