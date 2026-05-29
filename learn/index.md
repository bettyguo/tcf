---
layout: default
title: "Learn"
eyebrow: "Interactive learner studio"
subtitle: "Four browser-only tools that make the TCF Canada concrete: the NCLC scale, the exam structure, a per-section mock timer, and a 12-week trajectory replayer driven by real Phase-9 cohort data. No backend, no account — everything runs locally in your browser."
scripts:
  - /assets/js/learn.js
body_class: page-learn
---

<div class="callout callout-info">
  <p class="callout-title">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
    Why this page exists
  </p>
  <p>The fastest way to make a 210-hour training commitment <em>real</em> is to know exactly what you're aiming at. These four tools answer four questions a learner actually has on day one: what does NCLC <em>X</em> mean? what is the exam shaped like? what will the room feel like? and — given my starting point — what does the next 12 weeks actually look like?</p>
</div>

<nav class="learn-toc" aria-label="On this page">
  <a href="#nclc-explorer">① NCLC explorer</a>
  <a href="#exam-format">② Exam format</a>
  <a href="#mock-timer">③ Mock-section timer</a>
  <a href="#trajectory">④ Trajectory replayer</a>
</nav>

## ① The NCLC scale, made concrete {#nclc-explorer}

> NCLC (Niveaux de compétence linguistique canadiens) is the Canadian benchmark IRCC uses to score your French for permanent residence. The 12 levels are not evenly spaced — and they don't map 1-to-1 to CEFR. This explorer makes the scale tangible.

<section class="learn-card nclc-explorer">
  <div class="nclc-controls">
    <label for="nclc-level" class="nclc-control-label">Move the slider to explore a level</label>
    <div class="nclc-slider-wrap">
      <input type="range" id="nclc-level" min="3" max="11" step="1" value="7" aria-label="NCLC level" />
      <div class="nclc-ticks" aria-hidden="true">
        <span data-tick="3">3</span><span data-tick="4">4</span><span data-tick="5">5</span><span data-tick="6">6</span><span data-tick="7" class="is-target">7</span><span data-tick="8">8</span><span data-tick="9" class="is-target">9</span><span data-tick="10">10</span><span data-tick="11">11</span>
      </div>
    </div>
    <div class="nclc-quick-jumps">
      <button class="chip" data-jump="5">Where I might start</button>
      <button class="chip is-primary" data-jump="7">NCLC 7 — Express Entry "adequate"</button>
      <button class="chip is-primary" data-jump="9">NCLC 9 — francophone-stream max points</button>
      <button class="chip" data-jump="11">NCLC 11 — native-near</button>
    </div>
  </div>

  <div class="nclc-readout" id="nclc-readout">
    <!-- Filled by learn.js -->
  </div>
</section>

<p class="demo-note">Sources: IRCC's TCF Canada→NCLC equivalency charts (table reproduced from the published table valid as of 2026). CEFR mapping is approximate — CEFR and NCLC measure different things, and IRCC explicitly does not publish a CEFR equivalence; the column here is a learner-facing approximation, not the official mapping.</p>

## ② TCF Canada exam format — exactly what you'll sit {#exam-format}

> The TCF Canada is four mandatory sections in this order: CO → CE → EE → EO. The total seat time is roughly 2 h 47 m, although EO is scheduled separately at the test centre. Click any section to see its structure, the NCLC bands per raw-score, and an FEI-shaped sample question.

<section class="learn-card exam-format">
  <div class="exam-tabs" role="tablist" aria-label="TCF Canada sections">
    <button role="tab" aria-selected="true" data-section="CO" class="exam-tab is-active">
      <span class="exam-tab-tag">CO</span>
      <span class="exam-tab-name">Compréhension orale</span>
      <span class="exam-tab-meta">39 Q · 35 min</span>
    </button>
    <button role="tab" aria-selected="false" data-section="CE" class="exam-tab">
      <span class="exam-tab-tag">CE</span>
      <span class="exam-tab-name">Compréhension écrite</span>
      <span class="exam-tab-meta">39 Q · 60 min</span>
    </button>
    <button role="tab" aria-selected="false" data-section="EE" class="exam-tab">
      <span class="exam-tab-tag">EE</span>
      <span class="exam-tab-name">Expression écrite</span>
      <span class="exam-tab-meta">3 tâches · 60 min</span>
    </button>
    <button role="tab" aria-selected="false" data-section="EO" class="exam-tab">
      <span class="exam-tab-tag">EO</span>
      <span class="exam-tab-name">Expression orale</span>
      <span class="exam-tab-meta">3 tâches · 12 min</span>
    </button>
  </div>

  <div class="exam-panel" id="exam-panel" role="tabpanel" aria-live="polite">
    <!-- Filled by learn.js -->
  </div>
</section>

<p class="demo-note">The sample prompts shown are <strong>not FEI material</strong> — they're independently authored items in the FEI shape (per ADR-020, no FEI test material ships with the repo). Difficulty bands are approximated to A2/B1/B2/C1 per the published TCF descriptors.</p>

## ③ Mock-section timer — feel the clock {#mock-timer}

> Test-day stress comes from time pressure, not language gaps. Sit a single section against the real clock. Pick CO, CE, EE, or EO; press Start; experience the actual cadence. No questions are scored — this is purely a pacing tool.

<section class="learn-card mock-timer">
  <div class="mt-controls">
    <label for="mt-section">Section</label>
    <select id="mt-section" class="select">
      <option value="CO">CO — Compréhension orale (35 min)</option>
      <option value="CE" selected>CE — Compréhension écrite (60 min)</option>
      <option value="EE">EE — Expression écrite (60 min)</option>
      <option value="EO">EO — Expression orale (12 min)</option>
    </select>
    <div class="mt-buttons">
      <button class="btn btn-primary" id="mt-start">Start</button>
      <button class="btn btn-secondary" id="mt-pause" disabled>Pause</button>
      <button class="btn btn-ghost" id="mt-reset">Reset</button>
    </div>
  </div>

  <div class="mt-display" id="mt-display">
    <div class="mt-clock-wrap">
      <svg class="mt-ring" viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" r="52" class="mt-ring-bg" />
        <circle cx="60" cy="60" r="52" class="mt-ring-fg" id="mt-ring-fg" />
      </svg>
      <div class="mt-clock-text">
        <span class="mt-time" id="mt-time">60:00</span>
        <span class="mt-sublabel" id="mt-sublabel">CE — ready to start</span>
      </div>
    </div>

    <div class="mt-checkpoints" id="mt-checkpoints">
      <!-- Filled by learn.js — section-specific pacing checkpoints -->
    </div>
  </div>

  <p class="demo-note">Pacing checkpoints come from PEDAGOGY §6 — they're recommended per-question or per-task budgets, not exam rules. If you're past a checkpoint, slow down; if you're ahead, you have buffer for hard items.</p>
</section>

## ④ 12-week trajectory replayer {#trajectory}

> Pick a starting profile from the Phase-9 cohort audit. Watch the planner-simulator replay the 12-week training run, week by week. The shaded band is the 5th–95th percentile across 100 stochastic trajectories — the median is the line. The target NCLC is the red rule. The honest-refusal cohorts are why the readiness gate exists.

<section class="learn-card trajectory">
  <div class="traj-controls">
    <label for="traj-cohort">Cohort</label>
    <select id="traj-cohort" class="select">
      <!-- Filled by learn.js from pedagogy_audit.json (inlined) -->
    </select>
    <div class="mt-buttons">
      <button class="btn btn-primary" id="traj-play">▶ Play 12 weeks</button>
      <button class="btn btn-secondary" id="traj-step">Step +1 week</button>
      <button class="btn btn-ghost" id="traj-reset">Reset</button>
    </div>
  </div>

  <div class="traj-stage">
    <div class="traj-chart-wrap">
      <svg class="traj-chart" id="traj-chart" viewBox="0 0 600 280" aria-label="Trajectory chart"></svg>
    </div>
    <aside class="traj-meta" id="traj-meta">
      <!-- Filled by learn.js -->
    </aside>
  </div>

  <details class="traj-explain">
    <summary>What am I looking at?</summary>
    <ul>
      <li><strong>Solid line</strong> — simulated median of <em>min(skill)</em> across the four skills, week-by-week.</li>
      <li><strong>Shaded band</strong> — 5th–95th percentile across 100 trajectories with σ=0.25 of the learning rate per minute.</li>
      <li><strong>Dashed line</strong> — the planner's projection (a single deterministic forecast).</li>
      <li><strong>Red rule</strong> — target NCLC. The planner refuses to recommend booking until the line clears the rule <em>and</em> all four skills clear the ADR-025 confidence gate.</li>
    </ul>
  </details>
</section>

---

## Want to go deeper?

- **Why the planner over-weights production skills (EE/EO).** [PEDAGOGY §1]({{ '/PEDAGOGY/' | relative_url }}#1-the-eight-evidence-aligned-sla-principles) — Swain's output hypothesis is doing a lot of work here.
- **What the readiness gate actually checks.** [PEDAGOGY §5]({{ '/PEDAGOGY/' | relative_url }}#5-the-readiness-gate) and the live demo at [/try/]({{ '/try/' | relative_url }}#readiness-gate).
- **How the system measures itself.** [PEDAGOGY §7]({{ '/PEDAGOGY/' | relative_url }}#7-evidence-and-receipts) — the published κ tables and the 12-cohort calibration audit.
- **What it absolutely won't promise.** [LIMITATIONS.md]({{ '/LIMITATIONS/' | relative_url }}) — twelve things, in writing, with receipts.
