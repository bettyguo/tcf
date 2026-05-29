---
layout: default
title: "Architecture Decision Records"
eyebrow: "48 decisions"
subtitle: "Every load-bearing design choice in tcf-accel has a written rationale. Read these to understand what trade-off was made, why, and what would change our mind."
permalink: /adrs/
---

<p>The ADRs are ordered chronologically. Phases 1–8 added ADRs 0001–0045; Phase 9 (the launch) added 0046–0048.</p>

<ul class="adr-list">
  <li><span class="num">ADR-0001</span><a class="title" href="/tcf/docs/adrs/0001-monorepo-with-uv-and-pnpm/">Monorepo with `uv` (Python) and `pnpm` (JS)</a></li>
  <li><span class="num">ADR-0002</span><a class="title" href="/tcf/docs/adrs/0002-postgres-pgvector-over-separate-vector-db/">PostgreSQL 16 + `pgvector` initially; Qdrant as a swap-in</a></li>
  <li><span class="num">ADR-0003</span><a class="title" href="/tcf/docs/adrs/0003-fastapi-over-django-or-flask/">FastAPI over Django or Flask</a></li>
  <li><span class="num">ADR-0004</span><a class="title" href="/tcf/docs/adrs/0004-nextjs15-app-router/">Next.js 15 (App Router) over Remix / SvelteKit</a></li>
  <li><span class="num">ADR-0005</span><a class="title" href="/tcf/docs/adrs/0005-celery-redis-over-rq-dramatiq/">Celery + Redis over RQ / Dramatiq</a></li>
  <li><span class="num">ADR-0006</span><a class="title" href="/tcf/docs/adrs/0006-fsrs6-as-srs-algorithm/">FSRS-6 as the spaced-repetition algorithm</a></li>
  <li><span class="num">ADR-0007</span><a class="title" href="/tcf/docs/adrs/0007-whisper-large-v3-french-primary-asr/">`bofenghuang/whisper-large-v3-french` as the primary ASR</a></li>
  <li><span class="num">ADR-0008</span><a class="title" href="/tcf/docs/adrs/0008-camembert-cefr-classifier-over-zero-shot-llm/">CamemBERT-derived CEFR classifier over zero-shot LLM classification</a></li>
  <li><span class="num">ADR-0009</span><a class="title" href="/tcf/docs/adrs/0009-litellm-gateway-with-claude-sonnet-46-default/">`litellm` as the LLM gateway, Claude Sonnet 4.6 (`claude-sonnet-4-6`) as default</a></li>
  <li><span class="num">ADR-0010</span><a class="title" href="/tcf/docs/adrs/0010-mit-code-cc-by-sa-content-license/">MIT for code, CC BY-SA 4.0 for original learning content (and why not GPL)</a></li>
  <li><span class="num">ADR-0011</span><a class="title" href="/tcf/docs/adrs/0011-jsonb-item-content-over-polymorphic-tables/">JSONB `items.content` with Pydantic validation, over polymorphic per-module tables</a></li>
  <li><span class="num">ADR-0012</span><a class="title" href="/tcf/docs/adrs/0012-precomputed-schedule-cache-over-on-demand/">Pre-computed schedule cache (Redis) with explicit invalidation; no on-demand compute on the request path</a></li>
  <li><span class="num">ADR-0013</span><a class="title" href="/tcf/docs/adrs/0013-online-bayesian-per-skill-with-nightly-irt-refit/">Online streaming Bayesian update for per-skill posterior; nightly batch IRT refit for item difficulty</a></li>
  <li><span class="num">ADR-0014</span><a class="title" href="/tcf/docs/adrs/0014-error-code-taxonomy-stability-promise/">Error code taxonomy stability is a public-API promise</a></li>
  <li><span class="num">ADR-0015</span><a class="title" href="/tcf/docs/adrs/0015-pgvector-first-qdrant-as-swap-in/">pgvector first; Qdrant as a swap-in if scale demands (re-affirms ADR-0002 with explicit triggers)</a></li>
  <li><span class="num">ADR-0016</span><a class="title" href="/tcf/docs/adrs/0016-api-versioning-url-v1-additive-only/">API versioning — URL `/v1/`, additive-only; breaking changes ship under `/v2/` with ≥ 6 mo overlap</a></li>
  <li><span class="num">ADR-0017</span><a class="title" href="/tcf/docs/adrs/0017-privacy-default-local-only/">Privacy default = `local_only`; no cloud anything until explicit opt-in</a></li>
  <li><span class="num">ADR-0018</span><a class="title" href="/tcf/docs/adrs/0018-hybrid-scraped-passage-llm-question-authoring/">Hybrid scraped-passage + LLM-question item authoring</a></li>
  <li><span class="num">ADR-0019</span><a class="title" href="/tcf/docs/adrs/0019-adversarial-distractor-rejection-threshold/">Adversarial-distractor rejection threshold = 0.25 over 20 trials</a></li>
  <li><span class="num">ADR-0020</span><a class="title" href="/tcf/docs/adrs/0020-no-fei-test-material-in-repo/">No FEI test material in the repo; sample-link proxy only</a></li>
  <li><span class="num">ADR-0021</span><a class="title" href="/tcf/docs/adrs/0021-synthetic-item-cap-per-module/">Synthetic-item cap = 40% per module</a></li>
  <li><span class="num">ADR-0022</span><a class="title" href="/tcf/docs/adrs/0022-quota-matrix-as-hard-release-gate/">Quota matrix is a hard release gate, not a guideline</a></li>
  <li><span class="num">ADR-0023</span><a class="title" href="/tcf/docs/adrs/0023-fsrs6-default-weights-with-per-user-optimization-deferred/">FSRS-6 default weights initially; per-user optimization deferred to ≥ 100 reviews</a></li>
  <li><span class="num">ADR-0024</span><a class="title" href="/tcf/docs/adrs/0024-lector-spacing-bounded-by-fsrs/">LECTOR semantic-spacing penalty bounded so as not to overrule FSRS</a></li>
  <li><span class="num">ADR-0025</span><a class="title" href="/tcf/docs/adrs/0025-posterior-ci-mandatory-confidence-flag-launch-blocking/">Every NCLC point estimate ships with a credible interval; the `confident` flag is launch-blocking</a></li>
  <li><span class="num">ADR-0026</span><a class="title" href="/tcf/docs/adrs/0026-diagnostic-cat-mcq-rubric-production/">Diagnostic is computer-adaptive (CAT) for CO/CE; rubric-scored prompts for EE/EO</a></li>
  <li><span class="num">ADR-0027</span><a class="title" href="/tcf/docs/adrs/0027-allocator-overweights-production-skills/">The bottleneck-driven time allocator over-weights production skills (β_EE=1.4, β_EO=1.5)</a></li>
  <li><span class="num">ADR-0028</span><a class="title" href="/tcf/docs/adrs/0028-exam-shape-floor/">Exam-shape floor — hard floor + soft cadence</a></li>
  <li><span class="num">ADR-0029</span><a class="title" href="/tcf/docs/adrs/0029-co-single-play-and-lexical-alt/">CO single-play default; lexical alternative emits `module=CE`</a></li>
  <li><span class="num">ADR-0030</span><a class="title" href="/tcf/docs/adrs/0030-default-plan-shadowing-floor/">Mandatory 10-min/day shadowing reservation in default plans</a></li>
  <li><span class="num">ADR-0031</span><a class="title" href="/tcf/docs/adrs/0031-pronunciation-signal-coarse-proxy/">`PronunciationSignal` is a structural coarse-proxy contract</a></li>
  <li><span class="num">ADR-0032</span><a class="title" href="/tcf/docs/adrs/0032-canonical-vs-training-mock-modes/">Canonical and training mock modes</a></li>
  <li><span class="num">ADR-0033</span><a class="title" href="/tcf/docs/adrs/0033-mock-cadence-cap/">Mock-exam cadence cap (1/w → 2/w → 3/w)</a></li>
  <li><span class="num">ADR-0034</span><a class="title" href="/tcf/docs/adrs/0034-drill-mock-posterior-divergence-alert/">Track drill and mock posteriors separately; alert on divergence</a></li>
  <li><span class="num">ADR-0035</span><a class="title" href="/tcf/docs/adrs/0035-seeded-greedy-selector-not-ortools/">Mock-exam item selector — seeded greedy, not OR-Tools MIP</a></li>
  <li><span class="num">ADR-0036</span><a class="title" href="/tcf/docs/adrs/0036-hybrid-features-llm-calibration-architecture/">Auto-scoring uses a hybrid features + LLM + calibration architecture</a></li>
  <li><span class="num">ADR-0037</span><a class="title" href="/tcf/docs/adrs/0037-expert-labelled-set-launch-blocking/">Expert-labelled set (≥ 200 / skill) is launch-blocking for "claimed κ"</a></li>
  <li><span class="num">ADR-0038</span><a class="title" href="/tcf/docs/adrs/0038-publish-kappa-every-release/">Publish Cohen's κ with every release; experimental badge below 0.55</a></li>
  <li><span class="num">ADR-0039</span><a class="title" href="/tcf/docs/adrs/0039-llm-temperature-and-structured-output/">LLM critic uses temperature ≤ 0.2 + structured-output enforcement</a></li>
  <li><span class="num">ADR-0040</span><a class="title" href="/tcf/docs/adrs/0040-inflation-guard-clamp/">Inflation guard clamps LLM scores against the feature floor</a></li>
  <li><span class="num">ADR-0041</span><a class="title" href="/tcf/docs/adrs/0041-nextjs15-app-router-rsc-csc-split/">Next.js 15 App Router with RSC for static, CSC for interactive</a></li>
  <li><span class="num">ADR-0042</span><a class="title" href="/tcf/docs/adrs/0042-no-gamification/">No gamification — calm over engagement</a></li>
  <li><span class="num">ADR-0043</span><a class="title" href="/tcf/docs/adrs/0043-notifications-opt-in-zero-defaults/">Notifications are opt-in with zero defaults</a></li>
  <li><span class="num">ADR-0044</span><a class="title" href="/tcf/docs/adrs/0044-wcag-22-aa-launch-gate/">WCAG 2.2 AA is a launch gate across the app</a></li>
  <li><span class="num">ADR-0045</span><a class="title" href="/tcf/docs/adrs/0045-readiness-widget-two-green-mocks-required/">Readiness widget never shows 🟢 without ≥ 2 consecutive canonical mocks at 🟢</a></li>
  <li><span class="num">ADR-0046</span><a class="title" href="/tcf/docs/adrs/0046-launch-criteria-blocking-not-advisory/">Launch criteria are blocking, not advisory</a></li>
  <li><span class="num">ADR-0047</span><a class="title" href="/tcf/docs/adrs/0047-external-security-review-or-two-maintainer-fallback/">External security review for v1.0 (or two-maintainer sign-off as a fallback)</a></li>
  <li><span class="num">ADR-0048</span><a class="title" href="/tcf/docs/adrs/0048-public-publication-of-kappa-and-cohort-results-in-readme/">Public publication of κ + cohort-success simulation results in the README</a></li>
</ul>
