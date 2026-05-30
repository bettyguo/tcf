---
layout: default
title: "Glossary"
eyebrow: "Jargon decoder"
subtitle: "Every load-bearing acronym, statistical term, and pedagogical construct used on this site, in one place. Direct-anchor links so the rest of the docs can deep-link to a definition instead of repeating it."
description: "Glossary of tcf-accel terminology — NCLC, CEFR, TCF Canada, FEI, FSRS, IRT, Cohen's κ, posterior, credible interval, ADR, and 30+ more, with cross-references."
body_class: page-glossary
---

<div class="callout callout-info">
  <p class="callout-title">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
    Why a glossary?
  </p>
  <p>The docs index three different vocabularies: <strong>pedagogy</strong> (SLA, output hypothesis, shadowing), <strong>statistics</strong> (Bayesian posterior, IRT, Cohen's κ), and <strong>infrastructure</strong> (FSRS, ADR, JSONB). Every page assumes the reader already knows the terms it uses. This page is the fallback when an unfamiliar acronym derails a reader on the first paragraph.</p>
</div>

<nav class="learn-toc" aria-label="Jump to letter">
  <a href="#letter-a">A</a>
  <a href="#letter-b">B</a>
  <a href="#letter-c">C</a>
  <a href="#letter-d">D</a>
  <a href="#letter-e">E</a>
  <a href="#letter-f">F</a>
  <a href="#letter-i">I</a>
  <a href="#letter-j">J</a>
  <a href="#letter-k">K</a>
  <a href="#letter-l">L</a>
  <a href="#letter-m">M</a>
  <a href="#letter-n">N</a>
  <a href="#letter-o">O</a>
  <a href="#letter-p">P</a>
  <a href="#letter-r">R</a>
  <a href="#letter-s">S</a>
  <a href="#letter-t">T</a>
</nav>

<dl class="glossary">

<h2 id="letter-a">A</h2>

<dt id="adr">ADR — Architecture Decision Record</dt>
<dd>A short, dated document capturing a single load-bearing technical decision and the trade-offs that produced it. tcf-accel ships <strong>48 ADRs</strong>, indexed at <a href="{{ '/adrs/' | relative_url }}">/adrs/</a>. Each ADR is numbered 0001–0048 and immutable once accepted; supersession is recorded by adding a new ADR that points back.</dd>

<dt id="allocator">Allocator (bottleneck)</dt>
<dd>The planner sub-component that decides how to split today's minute budget across CO/CE/EE/EO. Formula (ADR-027): per-skill minutes ∝ max(ε, (target − mean)²) · β<sub>skill</sub>, where β<sub>EE</sub>=1.4 and β<sub>EO</sub>=1.5 over-weight the production skills. Production-skill floor 10 min/skill, 10 min/day shadowing reserve. Live demo at <a href="{{ '/try/' | relative_url }}#bottleneck-allocator">/try/ §3</a>.</dd>

<dt id="ase">ASR — Automatic Speech Recognition</dt>
<dd>The system uses Whisper-large-v3 (French primary; ADR-007) for EO turn transcription. Runs on-device by default per ADR-017 (privacy default — local-only).</dd>

<h2 id="letter-b">B</h2>

<dt id="beta">β-weight (bottleneck)</dt>
<dd>Per-skill multiplier in the <a href="#allocator">allocator</a>. β<sub>CO</sub>=β<sub>CE</sub>=1.0 (reception), β<sub>EE</sub>=1.4, β<sub>EO</sub>=1.5 (production). The over-weight reflects Swain's output hypothesis (1985): receiving comprehensible input is necessary but not sufficient — pushed-output volume drives production accuracy.</dd>

<h2 id="letter-c">C</h2>

<dt id="ce">CE — Compréhension écrite</dt>
<dd>Reading-comprehension section of the TCF Canada. 39 items in 60 minutes, four difficulty tiers (T1–T4). T4 (B2–C2 editorials) requires ~150 wpm with 80%+ comprehension to clear on time. Drill at <a href="{{ '/practice/#reading' | relative_url }}">/practice/#reading</a>.</dd>

<dt id="cefr">CEFR — Common European Framework of Reference for Languages</dt>
<dd>European six-level scale (A1, A2, B1, B2, C1, C2). CEFR and <a href="#nclc">NCLC</a> measure different things and IRCC explicitly does not publish a CEFR equivalence; the site shows a learner-facing approximation (NCLC 7 ≈ B2, NCLC 9 ≈ C1) but the official mapping for IRCC purposes is NCLC.</dd>

<dt id="co">CO — Compréhension orale</dt>
<dd>Listening-comprehension section of the TCF Canada. 39 items in 35 minutes — about 35 s per item plus the audio. ADR-029 commits to single-play training to match the exam shape. Drill at <a href="{{ '/practice/#listening' | relative_url }}">/practice/#listening</a>.</dd>

<dt id="confident">Confident (posterior flag)</dt>
<dd>An NCLC posterior is flagged <code>confident=True</code> iff <strong>n_obs ≥ 40</strong> AND <strong>variance ≤ 0.4</strong> AND ≥ 3 difficulty bands have been observed (ADR-025). The <a href="#gate">readiness gate</a> refuses 🟢 unless all four skills are confident.</dd>

<dt id="canonical-mock">Canonical mock</dt>
<dd>A full FEI-shape mock exam (CO + CE + EE + EO) drawn from the canonical pool. Distinguished from training mocks (ADR-032) — only canonical-mock results feed the readiness gate. Cadence cap: one canonical mock per 7 days (ADR-033).</dd>

<dt id="credible-interval">Credible interval (CI)</dt>
<dd>A Bayesian 95 % interval over the NCLC posterior. ADR-025 makes CI rendering mandatory: every NCLC point estimate ships with its CI, enforced by the <code>no-bare-nclc</code> ESLint rule. The system never shows a bare NCLC number. Live demo at <a href="{{ '/try/' | relative_url }}#credible-interval-renderer">/try/ §2</a>.</dd>

<h2 id="letter-d">D</h2>

<dt id="diagnostic">Diagnostic placement</dt>
<dd>Short calibrated screen run before training begins. Eight FEI-shape items (2 CO, 2 CE, 2 EE, 2 EO) returning a per-skill NCLC point estimate <em>with a wide CI</em>. The screen is a starting point, not a score. Run it at <a href="{{ '/practice/#diagnostic' | relative_url }}">/practice/#diagnostic</a>.</dd>

<dt id="dictee">Dictée</dt>
<dd>Listening-and-transcribe drill. The system plays a 1–4 sentence French passage once and grades a word-level diff with diacritic-sensitivity. Single-play matches the exam constraint (ADR-029). Drill at <a href="{{ '/practice/#listening' | relative_url }}">/practice/#listening</a>.</dd>

<dt id="distractor">Distractor</dt>
<dd>Wrong answer in a multiple-choice item. Authored distractors are screened by an adversarial rejection threshold (ADR-019) to remove implausible foils that inflate raw scores.</dd>

<h2 id="letter-e">E</h2>

<dt id="ee">EE — Expression écrite</dt>
<dd>Written-production section. Three tasks: Tâche 1 (≥60 mots, 8 min message), Tâche 2 (≥120 mots, 20 min account), Tâche 3 (≥180 mots, 32 min argumentative essay). Under-length triggers a deterministic penalty (ADR-028). Drill at <a href="{{ '/practice/#writing' | relative_url }}">/practice/#writing</a>.</dd>

<dt id="eo">EO — Expression orale</dt>
<dd>Spoken-production section. Three tasks in 12 minutes (entretien dirigé, échange d'informations, expression d'opinion). Scheduled separately from the written sections at the test centre. The repo does not run EO drills end-to-end against a cohort baseline; the locally hosted system does, with on-device <a href="#ase">ASR</a>.</dd>

<dt id="ease-factor">Ease factor</dt>
<dd>Per-card parameter in the <a href="#sm2">SM-2</a> algorithm controlling how fast intervals grow. Starts at 2.5; adjusts downward on failure. Cards with ease &lt; 1.3 are "leeches" and re-enter the new queue. See the leech list in the <a href="{{ '/practice/#stats' | relative_url }}">stats panel</a>.</dd>

<dt id="express-entry">Express Entry</dt>
<dd>The federal Canadian economic-immigration system. Awards points for French proficiency at <a href="#nclc">NCLC</a> 7 (adequate, ~25 points additive) and NCLC 9 (francophone-stream, full +50 additional points). The system's default target band is NCLC 7–9 because the points curve plateaus there.</dd>

<h2 id="letter-f">F</h2>

<dt id="fei">FEI — France Éducation International</dt>
<dd>The French public operator that designs and delivers the TCF Canada on behalf of the Ministère de l'Europe et des Affaires étrangères. ADR-020 commits that no FEI test material ships in this repo — every drill and mock item is independently authored in the FEI shape.</dd>

<dt id="fsrs">FSRS — Free Spaced Repetition Scheduler</dt>
<dd>The next-generation SRS algorithm chosen by ADR-006. v1.0 uses the default FSRS-6 weights (ADR-023) — per-user weight optimisation is deferred to v1.1+ because the cold-start volume per learner is too low for stable refitting.</dd>

<h2 id="letter-i">I</h2>

<dt id="ircc">IRCC — Immigration, Refugees and Citizenship Canada</dt>
<dd>The federal department that scores French proficiency for permanent-residence pathways using the <a href="#nclc">NCLC</a> table. IRCC publishes the TCF Canada→NCLC equivalency table; the system reproduces the published table valid as of 2026.</dd>

<dt id="irt">IRT — Item Response Theory</dt>
<dd>Statistical framework for modelling test-taker ability vs item difficulty. tcf-accel uses an online Bayesian per-skill posterior with a nightly IRT refit on the latest cohort responses (ADR-013).</dd>

<h2 id="letter-j">J</h2>

<dt id="jsonb">JSONB</dt>
<dd>PostgreSQL's binary JSON column type. ADR-011 chose JSONB for item content over polymorphic tables because the item-shape space is large and the query patterns are field-projection-heavy rather than relational.</dd>

<h2 id="letter-k">K</h2>

<dt id="kappa">κ — Cohen's quadratic-weighted kappa</dt>
<dd>Inter-rater agreement coefficient (−1 … 1, where 1 is perfect agreement and 0 is chance). Used here to measure how closely the auto-scorer agrees with human raters on the EE rubric. ADR-038 commits to publishing κ at every release; the table is on the landing page and at <a href="{{ '/data/calibration/ee.v1.report/' | relative_url }}">/data/calibration/ee.v1.report/</a>. v1.0 ships <em>κ_silver</em> (vs LLM critic); the 200-row <em>κ_gold</em> expert-rater set is a v1.1 commitment.</dd>

<h2 id="letter-l">L</h2>

<dt id="leech">Leech (SRS)</dt>
<dd>An SRS card the learner repeatedly fails (<a href="#ease-factor">ease</a> drops below 1.3). The system re-enters leeches into the new queue rather than letting them bury the daily review pile. Surfaced in the <a href="{{ '/practice/#stats' | relative_url }}">stats panel</a>.</dd>

<dt id="litellm">LiteLLM</dt>
<dd>Gateway library that abstracts LLM provider differences. ADR-009 sets Claude Sonnet 4.6 as the default LLM with LiteLLM as the gateway so the per-call provider is swappable without code changes.</dd>

<h2 id="letter-m">M</h2>

<dt id="mock">Mock exam</dt>
<dd>A timed end-to-end replica of one FEI exam day. Distinguished into <em>training mocks</em> (formative, frequent) and <em>canonical mocks</em> (summative, ADR-032) — only the latter feed the <a href="#gate">readiness gate</a>. See the section timer at <a href="{{ '/learn/#mock-timer' | relative_url }}">/learn/ §3</a>.</dd>

<h2 id="letter-n">N</h2>

<dt id="nclc">NCLC — Niveaux de compétence linguistique canadiens</dt>
<dd>The 12-level Canadian benchmark used by <a href="#ircc">IRCC</a> to score French proficiency. Levels 1–12, not evenly spaced, mapped to TCF Canada raw scores. NCLC 7 is the Express Entry "adequate" floor; NCLC 9 is the francophone-stream max-points threshold. Explore the scale at <a href="{{ '/learn/#nclc-explorer' | relative_url }}">/learn/ §1</a>.</dd>

<h2 id="letter-o">O</h2>

<dt id="output-hypothesis">Output hypothesis (Swain 1985)</dt>
<dd>The pedagogical claim that comprehensible <em>input</em> alone does not drive production accuracy — pushed <em>output</em> (writing, speaking) at the edge of current ability is required. Operationalised in the <a href="#allocator">allocator</a> via β<sub>EE</sub>=1.4, β<sub>EO</sub>=1.5.</dd>

<h2 id="letter-p">P</h2>

<dt id="pgvector">pgvector</dt>
<dd>Postgres extension for vector similarity search. ADR-002 + ADR-015 chose pgvector as the v1.0 vector store, with Qdrant as a swap-in if vector volume crosses the threshold where pgvector's IVFFlat index degrades.</dd>

<dt id="posterior">Posterior (Bayesian)</dt>
<dd>Probability distribution over a learner's NCLC <em>given</em> observed item responses. Combines a prior (initial belief) with the likelihood of observed responses under a Rasch model. Rendered in the UI as a <a href="#credible-interval">credible interval</a>, never a bare number.</dd>

<h2 id="letter-r">R</h2>

<dt id="readiness">Readiness gate</dt>
<dd>The system's anti-overconfidence rule (ADR-045). 🟢 (book the exam) requires <strong>all four skills posterior-confident</strong> AND <strong>two consecutive canonical mocks green</strong>. Any failure of the conjunction shows a degraded state with the priority-drills CTA — never the book-now CTA. Live demo at <a href="{{ '/try/' | relative_url }}#readiness-gate">/try/ §1</a>.</dd>

<h2 id="letter-s">S</h2>

<dt id="shadowing">Shadowing</dt>
<dd>A pronunciation drill where the learner repeats a native recording immediately after hearing it. ADR-024 bounds the spacing by FSRS so shadowing doesn't compete with the SRS schedule. The default plan reserves 10 min/day for shadowing (ADR-030).</dd>

<dt id="sla">SLA — Second-Language Acquisition</dt>
<dd>The pedagogy research field the system aligns to. Eight evidence-aligned SLA principles are operationalised in PEDAGOGY §1 — input hypothesis, output hypothesis, focus-on-form, spaced retrieval, deliberate practice, errorful learning, interleaving, and the testing effect.</dd>

<dt id="sm2">SM-2</dt>
<dd>The SuperMemo-2 spaced-repetition algorithm. Simpler than <a href="#fsrs">FSRS</a>; rates cards 1–5, grows intervals by an ease factor. The /practice/ vocab deck uses SM-2 (lightweight; FSRS in the hosted system). Reference: <a href="https://en.wikipedia.org/wiki/SuperMemo">SuperMemo on Wikipedia</a>.</dd>

<h2 id="letter-t">T</h2>

<dt id="tcf">TCF Canada</dt>
<dd>The Test de connaissance du français pour le Canada — the French proficiency test recognised by <a href="#ircc">IRCC</a> for the federal Express Entry programme. Delivered by <a href="#fei">FEI</a>. Four sections: CO, CE, EE, EO, totalling ~2 h 47 min seat time.</dd>

<dt id="ts">Training-set hash</dt>
<dd>A short SHA prefix attached to every published κ table identifying exactly which examples were used to fit the auto-scorer. Lets external reviewers reproduce the published numbers from the same examples (ADR-048).</dd>

</dl>

---

## Cross-references

Every entry on this page can be deep-linked. Use the anchor in the heading (e.g. <code>/glossary/#kappa</code>, <code>/glossary/#confident</code>). The site's other pages link to glossary entries instead of redefining terms inline, so a definition only needs to be maintained in one place.

If a term is missing here that you encountered elsewhere on the site, that's a docs bug — <a href="https://github.com/bettyguo/tcf/issues/new">please file an issue</a>.
