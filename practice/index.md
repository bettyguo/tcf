---
layout: default
title: "Practice"
eyebrow: "French training tools"
subtitle: "Six real, browser-only French drills. No backend, no account — your progress is saved locally. Diagnostic quiz that gives you a starting NCLC estimate, SRS vocabulary, listening dictation, timed writing (with autosave), reading speed test, and a verb-conjugation drill."
scripts:
  - /assets/js/practice.js
body_class: page-practice
---

<div class="callout callout-success">
  <p class="callout-title">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
    Real practice — no signup, fully offline-capable
  </p>
  <p>Every drill below runs in your browser. Audio uses your device's built-in TTS (no network). Progress is saved in <code>localStorage</code> only — clear your data, lose your progress. The 241-card vocabulary deck is CC BY-SA 4.0 and ships inline with the page bundle (<a href="https://github.com/bettyguo/tcf/blob/main/assets/js/practice.js">assets/js/practice.js</a>).</p>
</div>

<nav class="learn-toc" aria-label="On this page">
  <a href="#diagnostic">① Diagnostic placement</a>
  <a href="#vocab">② Vocabulary SRS</a>
  <a href="#listening">③ Listening dictée</a>
  <a href="#writing">④ Timed writing</a>
  <a href="#reading">⑤ Reading speed</a>
  <a href="#conjugation">⑥ Conjugation drill</a>
  <a href="#stats" class="ml-auto">Your stats</a>
</nav>

<section class="practice-hero" id="practice-overview">
  <div class="practice-streak-card">
    <div class="streak-badge"><span class="streak-num" data-stat="streak">0</span><span class="streak-label">day streak</span></div>
    <div class="streak-cells" data-stat="streak-cells" aria-label="Last 14 days of practice"></div>
    <p class="streak-meta">Total minutes: <strong data-stat="total-min">0</strong> · Sessions: <strong data-stat="sessions">0</strong> · Best streak: <strong data-stat="best-streak">0</strong></p>
    <div class="streak-spark">
      <p class="streak-spark-label">Last 30 days · minutes per day</p>
      <svg class="streak-spark-svg" id="streak-spark" viewBox="0 0 300 48" preserveAspectRatio="none" aria-label="Practice minutes, last 30 days"></svg>
    </div>
  </div>
</section>

## ① Where am I? — 8-question placement {#diagnostic}

> Eight calibrated items (2 CO, 2 CE, 2 EE, 2 EO). Takes 8–12 minutes. Returns a per-skill NCLC point estimate **with a credible interval** — the same shape the production system uses (ADR-025). This is a screen, not a score, and the CI will be wide.

<section class="learn-card diag-card" data-tool="diag">
  <div class="diag-intro" id="diag-intro">
    <p>You'll see eight items in a fixed order. Some are multiple-choice, two are open-ended. Don't look anything up — that defeats the calibration. We'll show your estimated NCLC for each of the four skills at the end.</p>
    <button class="btn btn-primary" id="diag-start">Start the placement →</button>
  </div>

  <div class="diag-stage" id="diag-stage" hidden>
    <div class="diag-progress">
      <span class="diag-progress-label">Item <strong id="diag-i">1</strong> of <strong id="diag-n">8</strong> · <span id="diag-skill">CO</span></span>
      <div class="diag-progress-bar"><span id="diag-progress-fg"></span></div>
    </div>
    <div class="diag-item" id="diag-item" aria-live="polite"></div>
  </div>

  <div class="diag-result" id="diag-result" hidden>
    <!-- Filled by practice.js with per-skill estimates -->
  </div>
</section>

<p class="demo-note">All eight items are independently authored in FEI-shape (no exam material ships with the repo per ADR-020). The calibration mapping (raw → NCLC) is a learner-facing approximation drawn from the published TCF Canada bands; the official mapping is held by FEI and applied by them.</p>

## ② Vocabulary — SM-2 spaced repetition {#vocab}

> 241 essential B1–B2 words and phrases for the TCF Canada, indexed by topic (Express Entry, civic life, work, school, daily life). Cards use the [SM-2 algorithm](https://en.wikipedia.org/wiki/SuperMemo) so the next-review interval grows with each correct answer. Rate yourself 1–5 after revealing the back. Press <span class="kbd">space</span> to reveal, then <span class="kbd">1</span>–<span class="kbd">5</span> to grade.

<section class="learn-card srs-card" data-tool="srs">
  <div class="srs-controls">
    <label for="srs-deck">Deck</label>
    <select id="srs-deck" class="select">
      <option value="all">All B1–B2 (241 cards)</option>
      <option value="ee_canada">Express Entry / Canadian civic life (48)</option>
      <option value="work">Work &amp; professional life (52)</option>
      <option value="school">School &amp; academic French (39)</option>
      <option value="daily">Daily life, money, health (62)</option>
      <option value="connectors">Connectors &amp; argumentation (40)</option>
    </select>
    <div class="srs-mode">
      <label><input type="radio" name="srs-dir" value="fr2en" checked> FR → EN</label>
      <label><input type="radio" name="srs-dir" value="en2fr"> EN → FR</label>
    </div>
  </div>

  <div class="srs-counters">
    <span class="srs-counter is-due"><strong data-srs="due">0</strong> due</span>
    <span class="srs-counter is-new"><strong data-srs="new">0</strong> new</span>
    <span class="srs-counter is-learned"><strong data-srs="learned">0</strong> learned</span>
  </div>

  <div class="srs-stage" id="srs-stage">
    <!-- Filled by practice.js -->
  </div>

  <div class="srs-help">
    <details>
      <summary>How rating works</summary>
      <ul>
        <li><strong>1 — Blackout.</strong> Reset interval to 1 day.</li>
        <li><strong>2 — Wrong, recognised on reveal.</strong> Interval halved (min 1 day).</li>
        <li><strong>3 — Correct, hard.</strong> Interval × 1.2.</li>
        <li><strong>4 — Correct, OK.</strong> Interval × ease (default 2.5).</li>
        <li><strong>5 — Easy.</strong> Interval × ease × 1.3.</li>
      </ul>
      <p>Ease starts at 2.5 and adjusts toward each rating. Cards with ease &lt; 1.3 are "leeches" and re-enter the new queue.</p>
    </details>
  </div>
</section>

## ③ Listening dictée — train CO under no-replay {#listening}

> ADR-029 commits to single-play training. The dictée plays one short French passage (one to four sentences), gives you a target window to type what you heard, then reveals the text and a word-level diff. Sentences are graded A2 → C1; pick a level matching your target NCLC band.

<section class="learn-card dict-card" data-tool="dict">
  <div class="dict-controls">
    <label for="dict-level">Level</label>
    <select id="dict-level" class="select">
      <option value="A2">A2 — Beginner (NCLC 4)</option>
      <option value="B1" selected>B1 — Threshold (NCLC 6)</option>
      <option value="B2">B2 — Adequate (NCLC 7–8)</option>
      <option value="C1">C1 — Advanced (NCLC 9–10)</option>
    </select>
    <label for="dict-rate">Playback rate</label>
    <select id="dict-rate" class="select">
      <option value="0.8">0.8× (slow)</option>
      <option value="1.0" selected>1.0× (natural)</option>
      <option value="1.15">1.15× (exam pace)</option>
    </select>
    <div class="mt-buttons">
      <button class="btn btn-primary" id="dict-play">▶ Play passage</button>
      <button class="btn btn-secondary" id="dict-replay" disabled>Replay (penalised)</button>
      <button class="btn btn-ghost" id="dict-skip">Skip</button>
    </div>
  </div>

  <textarea class="dict-input" id="dict-input" placeholder="Type what you hear…" rows="4" autocomplete="off" autocapitalize="sentences" spellcheck="false" lang="fr"></textarea>

  <div class="dict-actions">
    <button class="btn btn-primary" id="dict-check">Check</button>
    <span class="dict-meta" id="dict-meta">Words: 0 · Audio plays: 0</span>
  </div>

  <div class="dict-result" id="dict-result" hidden></div>

  <p class="demo-note">Uses your device's built-in French TTS via the Web Speech API. Quality varies by OS — on macOS / iOS the voices are excellent; on Windows install the "French (France)" voice in Settings → Time &amp; language. If your device has no French voice, the play button is disabled with a hint.</p>
</section>

## ④ Timed writing — EE shape, real word count {#writing}

> The TCF Canada EE has three tasks: 60-word message, 120-word account, 180-word argumentative essay. Pick a task, get a randomly chosen prompt, write under the real clock. Real-time word count + a soft register-coach that flags missing connectors, repetitive openings, and under-length.

<section class="learn-card write-card" data-tool="write">
  <div class="write-controls">
    <label for="write-task">Task</label>
    <select id="write-task" class="select">
      <option value="T1">Tâche 1 — Message (≥60 mots · 8 min)</option>
      <option value="T2">Tâche 2 — Compte-rendu (≥120 mots · 20 min)</option>
      <option value="T3" selected>Tâche 3 — Argumentatif (≥180 mots · 32 min)</option>
    </select>
    <div class="mt-buttons">
      <button class="btn btn-secondary" id="write-newprompt">New prompt</button>
      <button class="btn btn-primary" id="write-start">Start timer</button>
      <button class="btn btn-ghost" id="write-reset">Reset</button>
    </div>
  </div>

  <div class="write-prompt-box" id="write-prompt-box">
    <h4 class="write-prompt-label">Prompt</h4>
    <p class="write-prompt" id="write-prompt">Click "New prompt" to draw one at random.</p>
  </div>

  <textarea class="write-textarea" id="write-textarea" placeholder="Commencez ici…" rows="14" lang="fr" autocapitalize="sentences"></textarea>

  <div class="write-feedback">
    <div class="write-stat-row">
      <span class="write-stat"><span class="write-stat-label">Mots</span><strong id="write-words">0</strong> / <span id="write-target">180</span></span>
      <span class="write-stat"><span class="write-stat-label">Temps restant</span><strong id="write-time">32:00</strong></span>
      <span class="write-stat"><span class="write-stat-label">Phrases</span><strong id="write-sent">0</strong></span>
      <span class="write-stat"><span class="write-stat-label">Lex. unique</span><strong id="write-unique">0</strong>%</span>
    </div>
    <ul class="write-hints" id="write-hints" aria-live="polite"></ul>
  </div>

  <p class="demo-note">No grammar checker (those leak to a backend; ADR-031 forbids it for v1.0). The register-coach is heuristic — under-length triggers a deterministic penalty in the real EE rubric (ADR-028), and repeating the same opener across all three paragraphs hurts coherence. <a href="{{ '/PEDAGOGY/' | relative_url }}#1-the-eight-evidence-aligned-sla-principles">More on the SLA-aligned production focus →</a></p>
</section>

## ⑤ Reading speed — CE pace + comprehension {#reading}

> CE has 39 items in 60 minutes — roughly 92 s per item with T4 (B2–C2 editorials) at the back. This drill measures your WPM on a 400-word passage and a 3-item comprehension check. Hit ≥150 wpm with 2/3 correct to stay on T4-pace.

<section class="learn-card read-card" data-tool="read">
  <div class="read-controls">
    <label for="read-level">Level</label>
    <select id="read-level" class="select">
      <option value="B1">B1 — Article informatif</option>
      <option value="B2" selected>B2 — Reportage</option>
      <option value="C1">C1 — Éditorial</option>
    </select>
    <div class="mt-buttons">
      <button class="btn btn-primary" id="read-start">Start passage</button>
      <button class="btn btn-ghost" id="read-skip">New passage</button>
    </div>
    <div class="read-clock"><span id="read-time">00:00</span></div>
  </div>

  <div class="read-passage" id="read-passage">
    <p class="read-stub">Pick a level and press Start. The passage appears and a hidden timer begins.</p>
  </div>

  <div class="read-questions" id="read-questions" hidden>
    <!-- Comprehension Q rendered when user clicks "I've finished reading" -->
  </div>

  <div class="read-result" id="read-result" hidden></div>
</section>

## ⑥ Conjugation drill — the EE/EO bottleneck mechanic {#conjugation}

> Every B1 → B2 jump runs through the conditional, subjunctive, and the irregular passé-composé auxiliaries. This is a fast-fire drill: the system picks a verb, tense and pronoun; you type the form. Accent-tolerant grading; SM-2 ease tracks the verbs you keep missing. Press <span class="kbd">⏎</span> to submit, <span class="kbd">esc</span> to reveal.

<section class="learn-card conj-drill-card" data-tool="conjdrill">
  <div class="conj-drill-controls">
    <label for="cd-tense">Tenses in pool</label>
    <div class="cd-tense-pool" id="cd-tense-pool" role="group" aria-label="Tenses included in the drill">
      <label><input type="checkbox" value="présent" checked> présent</label>
      <label><input type="checkbox" value="passé_composé" checked> passé composé</label>
      <label><input type="checkbox" value="imparfait" checked> imparfait</label>
      <label><input type="checkbox" value="futur_simple" checked> futur simple</label>
      <label><input type="checkbox" value="conditionnel" checked> conditionnel</label>
      <label><input type="checkbox" value="subjonctif"> subjonctif</label>
    </div>
    <div class="cd-meta">
      <span class="cd-counter"><strong id="cd-correct">0</strong> correct</span>
      <span class="cd-counter cd-counter-wrong"><strong id="cd-wrong">0</strong> missed</span>
      <span class="cd-counter cd-counter-streak"><strong id="cd-streak">0</strong> streak</span>
    </div>
  </div>

  <div class="conj-drill-stage" id="cd-stage">
    <p class="muted">Pick at least one tense above and press <strong>Start</strong>.</p>
  </div>

  <div class="cd-actions">
    <button class="btn btn-primary" id="cd-start">Start drill</button>
    <button class="btn btn-secondary" id="cd-reveal" disabled>Reveal (esc)</button>
    <button class="btn btn-ghost" id="cd-reset">Reset score</button>
  </div>

  <p class="demo-note">Grading is accent-aware: missing accents are marked "diacritic" (half credit) instead of "wrong". The grader strips trailing pronouns from imperatives. If you need the full paradigm reference, the <a href="{{ '/tools/#conjugator' | relative_url }}">conjugator</a> in /tools/ is one tab away.</p>
</section>

---

## Your stats {#stats}

<section class="learn-card stats-card" data-tool="stats">
  <div class="stats-grid">
    <div class="stat-tile">
      <div class="stat-tile-label">Diagnostic NCLC (CO / CE / EE / EO)</div>
      <div class="stat-tile-val" data-stat="diag-summary">—</div>
    </div>
    <div class="stat-tile">
      <div class="stat-tile-label">Vocab cards learned</div>
      <div class="stat-tile-val"><span data-stat="vocab-learned">0</span> <span class="stat-sub">/ 241</span></div>
    </div>
    <div class="stat-tile">
      <div class="stat-tile-label">Dictées correct</div>
      <div class="stat-tile-val" data-stat="dict-ratio">0 / 0</div>
    </div>
    <div class="stat-tile">
      <div class="stat-tile-label">Writing tasks submitted</div>
      <div class="stat-tile-val" data-stat="write-count">0</div>
    </div>
    <div class="stat-tile">
      <div class="stat-tile-label">Median reading WPM</div>
      <div class="stat-tile-val" data-stat="read-wpm">—</div>
    </div>
    <div class="stat-tile">
      <div class="stat-tile-label">Total practice minutes</div>
      <div class="stat-tile-val" data-stat="total-min-2">0</div>
    </div>
    <div class="stat-tile">
      <div class="stat-tile-label">Conjugation drill — correct / total</div>
      <div class="stat-tile-val" data-stat="cd-ratio">0 / 0</div>
    </div>
  </div>
  <div class="leech-panel" id="leech-panel" hidden>
    <h4>Leeches — cards your ease has dropped below 1.5</h4>
    <p class="demo-note" style="margin-top:-4px;">These cards keep tripping you. Common causes: bad mnemonic, ambiguous meaning, or interference with a similar word. The system surfaces them so you can rebuild a hook (write the example sentence longhand, or pair the card with a personal anecdote) instead of just grinding through them again.</p>
    <ul class="leech-list" id="leech-list"></ul>
  </div>

  <div class="stats-actions">
    <button class="btn btn-secondary" id="stats-export">Export JSON</button>
    <button class="btn btn-secondary" id="stats-import">Import JSON…</button>
    <input class="stats-import-input" type="file" id="stats-import-file" accept="application/json,.json" />
    <button class="btn btn-ghost" id="stats-reset">Reset all progress</button>
  </div>
  <div class="stats-import-row">
    <p class="demo-note">All stats live in <code>localStorage</code> under the <code>tcf.practice.*</code> namespace. Exported JSON is a single, hashable file — move between browsers, share with a tutor, or feed it to your own dashboard. Import expects the same shape (validated client-side; bad files are rejected).</p>
  </div>
</section>

---

## Why these five, in this order?

The order mirrors the [PEDAGOGY dossier]({{ '/PEDAGOGY/' | relative_url }}) priority: **diagnose first** (you can't train what you haven't measured), **vocabulary and listening drive every other skill** (you can't write what you can't read, can't speak what you haven't heard), **then production**, then **pace**.

If you only have 20 minutes a day, the planner says: 5 min vocab + 8 min dictée + 7 min writing. The β=1.4/1.5 EE/EO over-weight ([ADR-027]({{ '/adrs/' | relative_url }})) is real, and reflected in the defaults above.

Want the same engines with full progress tracking, audio cohort comparison, and the planner that picks tomorrow's drills for you? [Self-host the production stack →]({{ '/OPERATIONS/' | relative_url }})
