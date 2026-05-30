---
layout: default
title: "Practice"
eyebrow: "French training tools"
subtitle: "Six real, browser-only French drills. No backend, no account — your progress is saved locally. Diagnostic quiz that gives you a starting NCLC estimate, SRS vocabulary, listening dictation, timed writing (with autosave), reading speed test, and a verb-conjugation drill."
scripts:
  - /assets/js/practice.js
  - /assets/js/extra-drills.js
  - /assets/js/more-drills.js
  - /assets/js/achievements.js
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
  <a href="#cloze">⑦ Sentence cloze</a>
  <a href="#numbers">⑧ Number listening</a>
  <a href="#rsvp">⑨ Speed reading</a>
  <a href="#voicerec">⑩ Voice recorder</a>
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

## ⑦ Sentence cloze — one blank, real grammar {#cloze}

> 40 hand-authored items targeting the failure points TCF graders flag most often: subjunctive triggers (B2 fault line), connectors (cohérence textuelle, EE rubric), prepositions, past-participle agreement, and Express-Entry-flavoured admin language. Accent-tolerant grading, with the rule explained on every miss.

<section class="learn-card cloze-card" data-tool="cloze">
  <div class="cloze-controls">
    <label for="cz-tag">Focus</label>
    <select id="cz-tag" class="select">
      <option value="all">All categories (40)</option>
      <option value="connector">Connectors</option>
      <option value="subjunctive">Subjunctive triggers</option>
      <option value="preposition">Prepositions</option>
      <option value="agreement">Past-participle agreement</option>
      <option value="article">Articles / partitives</option>
      <option value="pronoun">Pronouns</option>
      <option value="civic">Express Entry / civic</option>
      <option value="idiom">C1 idioms</option>
    </select>
    <div class="cloze-counters">
      <span class="cloze-counter"><strong id="cz-correct">0</strong>correct</span>
      <span class="cloze-counter"><strong id="cz-wrong">0</strong>wrong</span>
      <span class="cloze-counter"><strong id="cz-streak">0</strong>streak</span>
    </div>
  </div>

  <div class="cloze-intro" id="cz-intro">
    <p>Each item shows a sentence with one word missing. Type the missing word, press <strong>Enter</strong> to check. Press <strong>▶ Listen</strong> to hear the sentence (with your guess if you've typed one). Accents are nice-to-have, not required.</p>
    <button class="btn btn-primary" id="cz-start">Start cloze drill</button>
  </div>

  <div class="cloze-stage" id="cz-stage" aria-live="polite"></div>
</section>

<p class="demo-note">The 40 items aren't randomly authored — they target the eight categories the EE rubric grades against: <em>cohérence textuelle</em> (connectors), <em>maîtrise grammaticale</em> (subjunctive, agreement), and <em>lexique</em> (prepositions, idioms). Each item explains <em>why</em> on the explanation slide, not just <em>what</em>.</p>

---

## ⑧ Number listening — beat the CO ambush {#numbers}

> Numbers, dates, and prices are the most common single-play CO trap on the TCF Canada. <em>Quatre-vingt-quinze</em>, <em>soixante-douze euros cinquante</em>, <em>dix-huit heures quarante-cinq</em> — each takes one beat for a native, three for a B1 ear. This drill plays a number via your device's French TTS and asks you to type the digits.

<section class="learn-card numdrill-card" data-tool="numdrill">
  <div class="numdrill-controls">
    <div>
      <label class="nclc-control-label" for="nd-range">Range</label>
      <select id="nd-range" class="select">
        <option value="69">0–69 (no quatre-vingt-)</option>
        <option value="99" selected>0–99 (full)</option>
        <option value="999">0–999</option>
        <option value="9999">0–9 999</option>
        <option value="999999">0–999 999</option>
      </select>
    </div>
    <div class="nclc-quick-jumps nd-mode-chips" role="radiogroup" aria-label="Drill mode">
      <label class="chip is-primary"><input type="radio" name="nd-mode" value="int" checked> Integer</label>
      <label class="chip"><input type="radio" name="nd-mode" value="time"> Time (hh:mm)</label>
      <label class="chip"><input type="radio" name="nd-mode" value="money"> Money (€)</label>
    </div>
    <span class="numdrill-range">Active: <span class="ndr-active" id="nd-range-active">0–99</span></span>
    <div class="cloze-counters" style="margin-left:auto">
      <span class="cloze-counter"><strong id="nd-correct">0</strong>correct</span>
      <span class="cloze-counter"><strong id="nd-wrong">0</strong>wrong</span>
      <span class="cloze-counter"><strong id="nd-streak">0</strong>streak</span>
    </div>
  </div>

  <div class="cloze-intro" id="nd-intro">
    <p>Tap <strong>▶</strong> to hear a French number, then type what you heard. Press <strong>Enter</strong> to check, <strong>Ctrl/⌘ + space</strong> to replay. Time mode accepts <code>18:45</code>, <code>1845</code>, or <code>18h45</code>. Money mode accepts <code>12,50</code> or <code>12.50</code>. <strong>The drill auto-advances</strong> after every answer.</p>
    <button class="btn btn-primary" id="nd-start">Start number drill</button>
  </div>

  <div class="numdrill-stage" id="nd-stage" aria-live="polite"></div>
</section>

<p class="demo-note">Why this matters: on the real TCF Canada CO, audio plays exactly once (ADR-029). A number you can't decode in real time costs you the whole item — and CO items with numbers are over-represented in the practical-life cluster (train departures, prices, addresses, phone fragments). 5 minutes a day on this drill closes the gap fast because numbers are a small, finite ear-training space.</p>

---

## ⑨ Speed reading — RSVP + comprehension {#rsvp}

> Rapid Serial Visual Presentation flashes one word (or short chunk) at a time at a target words-per-minute, forcing your eyes to stop saccading. Six hand-authored passages span B1 → C1; each one is followed by a 3-question comprehension check. The aim: hit the T4 target of ≥150 WPM <em>with</em> ≥2/3 comprehension before you book the exam.

<section class="learn-card rsvp-card" data-tool="rsvp">
  <div class="rsvp-controls-row">
    <div>
      <label class="nclc-control-label" for="rs-level">Level</label>
      <select id="rs-level" class="select">
        <option value="B1">B1 — newcomer scenarios</option>
        <option value="B2" selected>B2 — opinion + analysis</option>
        <option value="C1">C1 — argumentative</option>
      </select>
    </div>
    <div>
      <label class="nclc-control-label" for="rs-chunk">Chunk</label>
      <select id="rs-chunk" class="select">
        <option value="1" selected>1 word</option>
        <option value="2">2 words</option>
        <option value="3">3 words</option>
      </select>
    </div>
    <div class="rsvp-wpm-wrap">
      <label class="nclc-control-label" for="rs-wpm">Target WPM · <span class="rsvp-wpm-num" id="rs-wpm-val">280</span></label>
      <input type="range" id="rs-wpm" min="120" max="500" step="20" value="280" aria-label="Target words per minute">
    </div>
  </div>

  <div class="rsvp-intro" id="rs-intro">
    <p>Press <strong>Start</strong> to flash a passage one chunk at a time. <strong>Space</strong> pauses, <strong>Esc</strong> stops early and jumps to the quiz. After the read, three multiple-choice questions check whether you actually parsed it — speed without comprehension is just scrolling.</p>
    <button class="btn btn-primary" id="rs-start">Start the RSVP →</button>
  </div>

  <div class="rsvp-stage" id="rs-stage" aria-live="polite"></div>
</section>

<p class="demo-note">Why chunking matters: native readers parse 2–3 word groups per fixation by default. Training with chunk=2 or 3 once the 1-word reading is stable transfers more cleanly to normal CE prose. Don't push WPM past comprehension — the "+20 WPM next time" button only earns its keep if comprehension stayed ≥2/3 this round.</p>

---

## ⑩ Voice recorder — hear yourself out {#voicerec}

> The cheapest, most underused EO drill: record your monologue, listen back, hear the pauses and hesitations you don't notice while speaking. Audio stays in your browser — nothing is uploaded, nothing is sent. The rubric checkboxes are for honest self-rating, not a score.

<section class="learn-card voicerec-card" data-tool="voicerec">
  <div class="rsvp-controls-row">
    <div>
      <label class="nclc-control-label" for="vr-prompt">Prompt</label>
      <select id="vr-prompt" class="select">
        <option value="t1_intro">T1 (60s) — self-introduction</option>
        <option value="t2_describe">T2 (90s) — narrate a trip</option>
        <option value="t3_argue">T3 (120s) — defend an opinion</option>
      </select>
    </div>
  </div>

  <div class="voicerec-intro" id="vr-intro">
    <p>The recorder uses your browser's microphone (you'll be asked once). Audio is stored in memory and never leaves the page — close the tab and it's gone. The 60–120 second cap matches the real TCF EO tasks; the VU meter helps you check your mic level before you start.</p>
    <button class="btn btn-primary" id="vr-start-gate">Open the recorder →</button>
  </div>

  <div class="voicerec-stage" id="vr-stage" aria-live="polite"></div>
</section>

<p class="demo-note">Privacy: the audio is a local Blob bound to a URL.createObjectURL handle. It's not written to disk, not sent over the network, not retained when the tab closes. The MediaRecorder API requires a secure context (https or localhost); on http you'll see a microphone-denied toast. The recorder won't run in Safari without WebKit's MediaRecorder fallback — Chrome / Edge / Firefox all work.</p>

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

  <div class="ach-host" data-achievements>
    <div class="ach-head"><h4>Achievements</h4><span class="ach-count">0 / 13</span></div>
    <div class="ach-grid"><span class="muted small">No data yet — start a drill above.</span></div>
  </div>
</section>

---

## Why these five, in this order?

The order mirrors the [PEDAGOGY dossier]({{ '/PEDAGOGY/' | relative_url }}) priority: **diagnose first** (you can't train what you haven't measured), **vocabulary and listening drive every other skill** (you can't write what you can't read, can't speak what you haven't heard), **then production**, then **pace**.

If you only have 20 minutes a day, the planner says: 5 min vocab + 8 min dictée + 7 min writing. The β=1.4/1.5 EE/EO over-weight ([ADR-027]({{ '/adrs/' | relative_url }})) is real, and reflected in the defaults above.

Want the same engines with full progress tracking, audio cohort comparison, and the planner that picks tomorrow's drills for you? [Self-host the production stack →]({{ '/OPERATIONS/' | relative_url }})
