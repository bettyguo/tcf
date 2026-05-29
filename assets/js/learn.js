/*
 * tcf-accel learner studio.
 * Four tools, all vanilla JS, all rendered client-side:
 *   ① NCLC explorer
 *   ② TCF Canada exam-format walkthrough
 *   ③ Mock-section timer
 *   ④ 12-week trajectory replayer (driven by Phase-9 cohort data, inlined)
 */
(function () {
  "use strict";

  /* ───────────────────────────────────────────────────────────
   * ① NCLC explorer
   * ───────────────────────────────────────────────────────── */

  // Per-NCLC level data. The "tcf_*" fields are approximate IRCC equivalency
  // bands for the TCF Canada per the publicly published charts. CEFR is a
  // learner-facing approximation; IRCC does not publish an official one.
  var NCLC = {
    3:  { cefr: "A1+", label: "Initial basic",
          summary: "Can handle short, predictable exchanges with strong support — greetings, simple questions, immediate needs.",
          can_do: ["Greet, introduce yourself, give basic personal information.",
                   "Understand very slow speech on familiar topics with repetition.",
                   "Write a few isolated sentences."],
          cannot_do: ["Follow most real conversations.", "Read a short newspaper article.",
                       "Sustain a 2-minute monologue without long pauses."],
          tcf: { CO: "200–298", CE: "200–298", EE: "4–5", EO: "4–5" },
          ee_irrc: false },
    4:  { cefr: "A2", label: "Developing basic",
          summary: "Can handle simple routine exchanges in familiar areas, but with effort.",
          can_do: ["Order food, ask directions, describe daily routine.",
                   "Read short signs, menus, simple personal notes.",
                   "Write a 40-word personal note (postcard, SMS)."],
          cannot_do: ["Follow news radio.", "Read a 400-word newspaper article.",
                       "Express opinions on abstract topics."],
          tcf: { CO: "299–330", CE: "299–330", EE: "6–7", EO: "6–7" },
          ee_irrc: false },
    5:  { cefr: "A2+ / B1−", label: "Initial intermediate",
          summary: "Can sustain straightforward conversations on familiar topics and handle most travel situations.",
          can_do: ["Handle routine travel/admin (bank, post office).",
                   "Understand the gist of a short news report.",
                   "Write a 100-word email about a planned event."],
          cannot_do: ["Argue a position in writing.", "Follow rapid native speech.",
                       "Read literary or specialised texts."],
          tcf: { CO: "331–368", CE: "331–374", EE: "8–9", EO: "8–9" },
          ee_irrc: false },
    6:  { cefr: "B1", label: "Developing intermediate",
          summary: "Can express opinions on familiar matters and follow most extended speech.",
          can_do: ["Describe experiences, opinions, plans clearly.",
                   "Follow main points of a longer broadcast.",
                   "Write a 150-word opinion email."],
          cannot_do: ["Discuss abstract topics with precision.",
                       "Read complex argumentation fluently.",
                       "Pass a TCF Canada at adequate level (NCLC 7)."],
          tcf: { CO: "331–368", CE: "331–374", EE: "8–9", EO: "8–9" },
          ee_irrc: false },
    7:  { cefr: "B2−", label: "Adequate intermediate proficiency",
          summary: "IRCC's bar for ‘adequate knowledge’ of French for permanent residence.",
          can_do: ["Sustain a 5-minute conversation on familiar abstract topics.",
                   "Read newspaper articles and form a critical reaction.",
                   "Write a 200-word argumentative paragraph."],
          cannot_do: ["Negotiate fluently in unfamiliar settings.",
                       "Follow rapid colloquial conversation between native speakers."],
          tcf: { CO: "369–397", CE: "375–405", EE: "10–11", EO: "10–11" },
          ee_irrc: true },
    8:  { cefr: "B2", label: "Fluent intermediate",
          summary: "Comfortably handles most workplace and academic French.",
          can_do: ["Hold an extended discussion on most familiar topics.",
                   "Understand a TED-style talk without subtitles.",
                   "Write a structured 300-word argumentative essay."],
          cannot_do: ["Master idiomatic native register in all contexts.",
                       "Read literary fiction fluently."],
          tcf: { CO: "398–457", CE: "406–452", EE: "12–13", EO: "12–13" },
          ee_irrc: true },
    9:  { cefr: "B2+ / C1−", label: "Advanced",
          summary: "Express Entry maximum points for the francophone stream apply here and above.",
          can_do: ["Argue a complex position spontaneously.",
                   "Read varied literature with effort but without aid.",
                   "Write a 400-word structured essay with nuance."],
          cannot_do: ["Sound entirely native in idiomatic register.",
                       "Master highly specialised technical vocabulary without prep."],
          tcf: { CO: "458–502", CE: "453–498", EE: "14–15", EO: "14–15" },
          ee_irrc: true },
    10: { cefr: "C1", label: "Native-like advanced",
          summary: "Sustained fluency, register awareness, and precise written argumentation.",
          can_do: ["Negotiate a contract entirely in French.",
                   "Follow rapid native colloquial speech.",
                   "Write a 500-word academic essay with rhetorical control."],
          cannot_do: ["Be undetectable as L2 in all contexts."],
          tcf: { CO: "503–548", CE: "499–549", EE: "16–17", EO: "16–17" },
          ee_irrc: true },
    11: { cefr: "C1+ / C2−", label: "Native-near",
          summary: "Effective full mastery for almost any professional or academic context.",
          can_do: ["Function fully in French academic / professional life.",
                   "Produce highly nuanced writing on demand.",
                   "Code-switch register fluently."],
          cannot_do: ["A small set of native idiomatic ceilings remain — but they don't affect IRCC scoring."],
          tcf: { CO: "549–698", CE: "550–699", EE: "18–20", EO: "18–20" },
          ee_irrc: true }
  };

  function renderNclc(level) {
    var d = NCLC[level];
    if (!d) return;
    var readout = document.getElementById("nclc-readout");
    if (!readout) return;
    var ircc = d.ee_irrc
      ? '<span class="status-pill status-ok">IRCC Express Entry: meets adequate threshold</span>'
      : '<span class="status-pill status-warn">IRCC Express Entry: below adequate threshold (NCLC 7+)</span>';
    var canHtml = d.can_do.map(function (s) { return "<li>" + s + "</li>"; }).join("");
    var cantHtml = d.cannot_do.map(function (s) { return "<li>" + s + "</li>"; }).join("");
    readout.innerHTML =
      '<div class="nclc-heading">' +
        '<div class="nclc-num"><span class="nclc-num-label">NCLC</span><span class="nclc-num-val">' + level + '</span></div>' +
        '<div class="nclc-titles">' +
          '<h3>' + d.label + '</h3>' +
          '<p class="nclc-cefr">≈ CEFR ' + d.cefr + '</p>' +
        '</div>' +
        '<div class="nclc-ircc">' + ircc + '</div>' +
      '</div>' +
      '<p class="nclc-summary">' + d.summary + '</p>' +
      '<div class="nclc-grid">' +
        '<div class="nclc-can"><h4>What a learner here <em>can</em> do</h4><ul>' + canHtml + '</ul></div>' +
        '<div class="nclc-cant"><h4>What a learner here can\'t do <em>yet</em></h4><ul>' + cantHtml + '</ul></div>' +
        '<div class="nclc-tcf">' +
          '<h4>Approximate TCF Canada bands</h4>' +
          '<table><thead><tr><th>Section</th><th>Raw score</th></tr></thead><tbody>' +
            '<tr><td>CO (listening)</td><td><code>' + d.tcf.CO + '</code></td></tr>' +
            '<tr><td>CE (reading)</td><td><code>' + d.tcf.CE + '</code></td></tr>' +
            '<tr><td>EE (writing)</td><td><code>' + d.tcf.EE + ' / 20</code></td></tr>' +
            '<tr><td>EO (speaking)</td><td><code>' + d.tcf.EO + ' / 20</code></td></tr>' +
          '</tbody></table>' +
        '</div>' +
      '</div>';

    // Sync the active tick.
    document.querySelectorAll(".nclc-ticks span").forEach(function (t) {
      t.classList.toggle("is-active", parseInt(t.dataset.tick, 10) === level);
    });
  }

  var nclcInput = document.getElementById("nclc-level");
  if (nclcInput) {
    nclcInput.addEventListener("input", function () {
      renderNclc(parseInt(nclcInput.value, 10));
    });
    document.querySelectorAll(".nclc-quick-jumps .chip").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var v = parseInt(btn.dataset.jump, 10);
        nclcInput.value = v;
        renderNclc(v);
      });
    });
    renderNclc(parseInt(nclcInput.value, 10));
  }

  /* ───────────────────────────────────────────────────────────
   * ② TCF Canada exam-format walkthrough
   * ───────────────────────────────────────────────────────── */

  var EXAM = {
    CO: {
      name: "Compréhension orale",
      english: "Listening comprehension",
      minutes: 35,
      questions: "39 MCQ, single audio play (ADR-029)",
      structure: [
        { label: "Tâche 1 — Échanges courts",       count: 10, band: "A1–A2", note: "Identify the situation from a short utterance." },
        { label: "Tâche 2 — Annonces / messages",    count: 8,  band: "A2–B1", note: "Public announcements; transactional dialogues." },
        { label: "Tâche 3 — Reportages / interviews", count: 12, band: "B1–B2", note: "News reports, short interviews, weather, sports." },
        { label: "Tâche 4 — Exposés courts",         count: 9,  band: "B2–C2", note: "Longer monologues, conferences, debates." }
      ],
      scoring: "Raw score 100–699 → NCLC 1–11. Adequate (NCLC 7) ≈ 369–397.",
      sample_q: "Dans le message, la personne…",
      sample_options: [
        "annule un rendez-vous chez le médecin.",
        "confirme un rendez-vous pour mardi.",
        "demande de déplacer un rendez-vous.",
        "se plaint d'une longue attente."
      ],
      sample_correct: 2,
      tip: "Single play — train under the no-replay constraint from week 1 (ADR-029)."
    },
    CE: {
      name: "Compréhension écrite",
      english: "Reading comprehension",
      minutes: 60,
      questions: "39 MCQ across four tasks",
      structure: [
        { label: "Tâche 1 — Messages courts",     count: 10, band: "A1–A2", note: "Notes, ads, schedules — identify a fact." },
        { label: "Tâche 2 — Notes informatives",   count: 8,  band: "A2–B1", note: "Personal correspondence, FAQ pages." },
        { label: "Tâche 3 — Articles informatifs", count: 12, band: "B1–B2", note: "News articles, factual reports." },
        { label: "Tâche 4 — Articles argumentatifs", count: 9,  band: "B2–C2", note: "Editorials, opinion pieces with implicit meaning." }
      ],
      scoring: "Raw score 100–699 → NCLC 1–11. Adequate (NCLC 7) ≈ 375–405.",
      sample_q: "L'auteur de cet éditorial pense surtout que la décision…",
      sample_options: [
        "est nécessaire mais mal expliquée.",
        "ne tient pas compte des coûts à long terme.",
        "satisfera les principaux acteurs concernés.",
        "manque d'ambition compte tenu de l'urgence."
      ],
      sample_correct: 4,
      tip: "Skim T4 first if you sit at NCLC 8+ — distractors are paraphrastic, not lexical."
    },
    EE: {
      name: "Expression écrite",
      english: "Written expression",
      minutes: 60,
      questions: "3 tasks: 60-, 120-, 180-word minimums",
      structure: [
        { label: "Tâche 1 — Message", count: 1, band: "A2",
          note: "≥ 60 words — short message (invitation, request) with explicit constraints." },
        { label: "Tâche 2 — Article / compte-rendu", count: 1, band: "B1",
          note: "≥ 120 words — structured account of an experience or event." },
        { label: "Tâche 3 — Texte argumentatif", count: 1, band: "B2–C1",
          note: "≥ 180 words — argumentative essay with clear position + counter-argument." }
      ],
      scoring: "Each task scored 0–6 across multiple criteria → 0–20. Adequate (NCLC 7) ≈ 10–11.",
      sample_q: "Tâche 3 (180 mots) — « Faut-il limiter le temps d'écran des enfants ? »",
      sample_options: null,
      sample_correct: null,
      tip: "Hit the word count — under-length is a deterministic score penalty (ADR-028). Use the planner's β_EE = 1.4 over-weight."
    },
    EO: {
      name: "Expression orale",
      english: "Spoken expression",
      minutes: 12,
      questions: "3 tasks, in-person with examiner",
      structure: [
        { label: "Tâche 1 — Entretien dirigé", count: 1, band: "A2",
          note: "≈ 1.5 min — examiner asks 5–6 personal questions." },
        { label: "Tâche 2 — Interaction",      count: 1, band: "B1",
          note: "≈ 3.5 min — request information from the examiner (role-play)." },
        { label: "Tâche 3 — Expression d'un point de vue", count: 1, band: "B2–C1",
          note: "≈ 5 min — present and defend an opinion on a topic the examiner picks." }
      ],
      scoring: "Each task scored 0–6 → 0–20. Adequate (NCLC 7) ≈ 10–11.",
      sample_q: "Tâche 3 — « Préférez-vous vivre en ville ou à la campagne ? Pourquoi ? »",
      sample_options: null,
      sample_correct: null,
      tip: "Practice 1-min, 3-min, 5-min timed monologues. The β_EO = 1.5 over-weight is the most aggressive in the allocator."
    }
  };

  function renderExam(section) {
    var d = EXAM[section];
    var panel = document.getElementById("exam-panel");
    if (!d || !panel) return;
    var rows = d.structure.map(function (s) {
      return '<tr><td>' + s.label + '</td><td><code>' + s.count + '</code></td><td><code>' + s.band + '</code></td><td>' + s.note + '</td></tr>';
    }).join("");
    var sampleHtml = "";
    if (d.sample_options) {
      var opts = d.sample_options.map(function (o, i) {
        var n = i + 1;
        var isCorrect = n === d.sample_correct;
        return '<li class="exam-opt' + (isCorrect ? ' is-correct' : '') + '"><span class="exam-opt-letter">' + String.fromCharCode(64 + n) + '</span><span>' + o + '</span>' + (isCorrect ? ' <span class="exam-opt-mark">✓</span>' : '') + '</li>';
      }).join("");
      sampleHtml = '<div class="exam-sample"><h4>Sample item (FEI-shape, independently authored — see ADR-020)</h4>' +
        '<p class="exam-q">' + d.sample_q + '</p><ol class="exam-options">' + opts + '</ol></div>';
    } else {
      sampleHtml = '<div class="exam-sample"><h4>Sample prompt (independently authored, FEI-shape)</h4>' +
        '<p class="exam-q exam-q-open">' + d.sample_q + '</p></div>';
    }

    panel.innerHTML =
      '<div class="exam-head">' +
        '<div><h3>' + d.name + ' <span class="exam-en">· ' + d.english + '</span></h3>' +
        '<p class="exam-meta"><span class="pill"><strong>' + d.minutes + ' min</strong></span> <span class="pill">' + d.questions + '</span></p></div>' +
        '<div class="exam-scoring">' + d.scoring + '</div>' +
      '</div>' +
      '<table class="exam-structure">' +
      '<thead><tr><th>Task</th><th>Items</th><th>Difficulty</th><th>Description</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table>' +
      sampleHtml +
      '<div class="callout callout-success exam-tip"><p class="callout-title">Strategy</p><p>' + d.tip + '</p></div>';
  }

  document.querySelectorAll(".exam-tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      document.querySelectorAll(".exam-tab").forEach(function (t) {
        t.classList.remove("is-active");
        t.setAttribute("aria-selected", "false");
      });
      tab.classList.add("is-active");
      tab.setAttribute("aria-selected", "true");
      renderExam(tab.dataset.section);
    });
    // Keyboard: ←/→ between tabs
    tab.addEventListener("keydown", function (e) {
      var tabs = Array.prototype.slice.call(document.querySelectorAll(".exam-tab"));
      var i = tabs.indexOf(tab);
      if (e.key === "ArrowRight") { e.preventDefault(); tabs[(i + 1) % tabs.length].click(); tabs[(i + 1) % tabs.length].focus(); }
      if (e.key === "ArrowLeft")  { e.preventDefault(); tabs[(i - 1 + tabs.length) % tabs.length].click(); tabs[(i - 1 + tabs.length) % tabs.length].focus(); }
    });
  });
  if (document.getElementById("exam-panel")) renderExam("CO");

  /* ───────────────────────────────────────────────────────────
   * ③ Mock-section timer
   * ───────────────────────────────────────────────────────── */

  // Per-section checkpoints — recommended pace per the PEDAGOGY dossier.
  // Each entry is a list of {at_minute, label}.
  var CHECKPOINTS = {
    CO: [
      { at: 9,  label: "T1 done (10 Q · ~9 min)" },
      { at: 16, label: "T2 done (8 Q · ~7 min)" },
      { at: 26, label: "T3 done (12 Q · ~10 min)" },
      { at: 34, label: "T4 done (9 Q · ~8 min)" },
      { at: 35, label: "Section end" }
    ],
    CE: [
      { at: 8,  label: "T1 done (10 Q)" },
      { at: 17, label: "T2 done (8 Q)" },
      { at: 38, label: "T3 done (12 Q)" },
      { at: 56, label: "T4 done (9 Q)" },
      { at: 60, label: "Buffer + review" }
    ],
    EE: [
      { at: 8,   label: "T1 (≥ 60 mots) drafted + checked" },
      { at: 28,  label: "T2 (≥ 120 mots) drafted + checked" },
      { at: 56,  label: "T3 (≥ 180 mots) drafted + checked" },
      { at: 60,  label: "Final read-through" }
    ],
    EO: [
      { at: 2,  label: "T1 (~1.5 min) — entretien dirigé" },
      { at: 6,  label: "T2 (~3.5 min) — interaction" },
      { at: 12, label: "T3 (~5 min) — point de vue" }
    ]
  };

  var mt = { sec: "CE", running: false, remaining: 60 * 60, timer: null, total: 60 * 60 };

  function mtFormat(s) {
    var m = Math.floor(s / 60), r = s % 60;
    return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r;
  }

  function mtRenderCheckpoints() {
    var box = document.getElementById("mt-checkpoints");
    if (!box) return;
    var checkpoints = CHECKPOINTS[mt.sec];
    var total = EXAM[mt.sec].minutes;
    var elapsed = (total * 60 - mt.remaining) / 60;
    var html = '<h4>Pacing checkpoints</h4><ul>';
    checkpoints.forEach(function (cp) {
      var done = elapsed >= cp.at;
      var pct = (cp.at / total) * 100;
      html += '<li class="' + (done ? "is-done" : "") + '" style="--cp-at:' + pct.toFixed(1) + '%">' +
        '<span class="mt-cp-time">' + cp.at + ' min</span>' +
        '<span class="mt-cp-label">' + cp.label + '</span>' +
        '<span class="mt-cp-mark" aria-hidden="true">' + (done ? "✓" : "○") + '</span>' +
        '</li>';
    });
    html += '</ul>';
    box.innerHTML = html;
  }

  function mtRender() {
    var time = document.getElementById("mt-time");
    var sub = document.getElementById("mt-sublabel");
    var ring = document.getElementById("mt-ring-fg");
    if (!time) return;
    time.textContent = mtFormat(mt.remaining);
    var pct = mt.total > 0 ? (mt.total - mt.remaining) / mt.total : 0;
    if (ring) {
      var C = 2 * Math.PI * 52;
      ring.setAttribute("stroke-dasharray", C.toFixed(2));
      ring.setAttribute("stroke-dashoffset", (C * (1 - pct)).toFixed(2));
    }
    sub.textContent = mt.sec + " — " + (mt.running ? "running" : mt.remaining === mt.total ? "ready to start" : mt.remaining === 0 ? "complete" : "paused");
    mtRenderCheckpoints();
  }

  function mtSet(section) {
    mt.sec = section;
    mt.total = EXAM[section].minutes * 60;
    mt.remaining = mt.total;
    mt.running = false;
    if (mt.timer) clearInterval(mt.timer);
    mt.timer = null;
    document.getElementById("mt-pause").disabled = true;
    document.getElementById("mt-start").disabled = false;
    document.getElementById("mt-start").textContent = "Start";
    mtRender();
  }

  function mtTick() {
    if (!mt.running) return;
    mt.remaining = Math.max(0, mt.remaining - 1);
    if (mt.remaining === 0) {
      mt.running = false;
      clearInterval(mt.timer);
      mt.timer = null;
      // Restore button affordances on natural completion.
      var startBtn = document.getElementById("mt-start");
      var pauseBtn = document.getElementById("mt-pause");
      if (startBtn) { startBtn.disabled = false; startBtn.textContent = "Start"; }
      if (pauseBtn) { pauseBtn.disabled = true; }
      var disp = document.getElementById("mt-display");
      if (disp) disp.classList.add("is-finished");
    }
    mtRender();
  }

  var mtSel = document.getElementById("mt-section");
  var mtStart = document.getElementById("mt-start");
  var mtPause = document.getElementById("mt-pause");
  var mtReset = document.getElementById("mt-reset");
  if (mtSel && mtStart && mtPause && mtReset) {
    mtSel.addEventListener("change", function () { mtSet(mtSel.value); });
    mtStart.addEventListener("click", function () {
      if (!mt.running) {
        mt.running = true;
        if (mt.remaining === 0) mt.remaining = mt.total;
        mt.timer = setInterval(mtTick, 1000);
        mtStart.textContent = "Resume";
        mtStart.disabled = true;
        mtPause.disabled = false;
        document.getElementById("mt-display").classList.remove("is-finished");
        mtRender();
      }
    });
    mtPause.addEventListener("click", function () {
      mt.running = false;
      if (mt.timer) clearInterval(mt.timer);
      mt.timer = null;
      mtStart.disabled = false;
      mtPause.disabled = true;
      mtStart.textContent = "Resume";
      mtRender();
    });
    mtReset.addEventListener("click", function () { mtSet(mt.sec); });
    mtSet("CE");
  }

  /* ───────────────────────────────────────────────────────────
   * ④ Trajectory replayer
   * Driven by Phase-9 cohort data, inlined here so the page is
   * self-sufficient (no fetch + CORS surprises on GitHub Pages).
   * ───────────────────────────────────────────────────────── */

  // Subset of fields from data/audit/phase9/pedagogy_audit.json — kept in sync
  // with the file. Inlined to avoid a CORS-sensitive fetch from Pages.
  var COHORTS = [
    { id: "solid_B1_target_NCLC7",     kind: "realistic",       target: 7,  init: 5.0, finalMin: 7.15,  med5: 7.128, med95: 7.173, plan: 7.10, p: 1.00 },
    { id: "solid_B1_target_NCLC9",     kind: "honest_refusal",  target: 9,  init: 5.0, finalMin: 7.20,  med5: 7.138, med95: 7.264, plan: 7.20, p: 0.00 },
    { id: "uneven_target_NCLC7",       kind: "realistic",       target: 7,  init: 4.0, finalMin: 7.15,  med5: 7.130, med95: 7.183, plan: 7.10, p: 1.00 },
    { id: "strong_B2_target_NCLC9",    kind: "realistic",       target: 9,  init: 7.0, finalMin: 9.15,  med5: 9.127, med95: 9.175, plan: 9.10, p: 1.00 },
    { id: "aggressive_B1_target_C2",   kind: "honest_refusal",  target: 11, init: 5.0, finalMin: 7.06,  med5: 7.008, med95: 7.138, plan: 7.10, p: 0.00 },
    { id: "short_runway_target_NCLC7", kind: "honest_refusal",  target: 7,  init: 5.0, finalMin: 6.10,  med5: 6.046, med95: 6.150, plan: 6.10, p: 0.00 },
    { id: "low_budget_target_NCLC7",   kind: "honest_refusal",  target: 7,  init: 5.0, finalMin: 5.75,  med5: 5.720, med95: 5.774, plan: 5.80, p: 0.00 },
    { id: "already_at_target",         kind: "trivial",         target: 9,  init: 9.0, finalMin: 9.78,  med5: 9.753, med95: 9.822, plan: 9.80, p: 1.00 },
    { id: "heritage_production_gap",   kind: "realistic",       target: 7,  init: 4.0, finalMin: 7.38,  med5: 7.335, med95: 7.439, plan: 7.40, p: 1.00 },
    { id: "reception_only_weakness",   kind: "realistic",       target: 7,  init: 4.0, finalMin: 7.22,  med5: 7.189, med95: 7.254, plan: 7.20, p: 1.00 },
    { id: "ee_bottleneck_only",        kind: "realistic",       target: 8,  init: 4.0, finalMin: 8.24,  med5: 8.212, med95: 8.275, plan: 8.20, p: 1.00 },
    { id: "eo_bottleneck_only",        kind: "realistic",       target: 8,  init: 4.0, finalMin: 8.23,  med5: 8.210, med95: 8.271, plan: 8.20, p: 1.00 }
  ];

  var WEEKS = 12;

  // Build a smooth interpolation init → finalMin over WEEKS weeks, with a mild
  // logistic-ish curve so the visual mirrors typical trajectory shapes.
  function curve(start, end) {
    var pts = [];
    for (var w = 0; w <= WEEKS; w++) {
      var t = w / WEEKS;
      // Smoothstep + slight saturation toward the end.
      var s = t * t * (3 - 2 * t);
      pts.push(start + (end - start) * s);
    }
    return pts;
  }

  function jitter(curve, frac) {
    return curve.map(function (v, i) {
      // Wider band mid-training; tighter at boundaries.
      var w = i / (curve.length - 1);
      var spread = Math.sin(Math.PI * w) * frac;
      return spread;
    });
  }

  var traj = { idx: 0, week: 0, anim: null };

  function cohortReadable(id) {
    return id.replace(/_/g, " ").replace(/\bnclc(\d+)\b/i, "NCLC $1").replace(/^./, function (c) { return c.toUpperCase(); });
  }

  function renderTrajChart(cohort, currentWeek) {
    var svg = document.getElementById("traj-chart");
    if (!svg) return;
    var W = 600, H = 280, PAD = { l: 44, r: 18, t: 18, b: 36 };
    var xs = function (w) { return PAD.l + (w / WEEKS) * (W - PAD.l - PAD.r); };
    var yMin = 3, yMax = 12;
    var ys = function (v) { return PAD.t + (1 - (v - yMin) / (yMax - yMin)) * (H - PAD.t - PAD.b); };

    var med = curve(cohort.init, cohort.finalMin);
    var planLine = curve(cohort.init, cohort.plan);
    // Symmetric jitter scaled to (med95 - med5)/2 at full mid.
    var halfBand = Math.max(0.05, (cohort.med95 - cohort.med5) / 2);
    var spread = jitter(med, halfBand * 4); // exaggerate mid-curve uncertainty
    var lo = med.map(function (v, i) { return v - spread[i]; });
    var hi = med.map(function (v, i) { return v + spread[i]; });

    var k = Math.min(WEEKS, Math.max(0, currentWeek));

    function path(arr, upto) {
      var pts = [];
      for (var i = 0; i <= upto; i++) pts.push(xs(i) + "," + ys(arr[i]));
      return "M " + pts.join(" L ");
    }
    function area(loArr, hiArr, upto) {
      var top = [];
      var bot = [];
      for (var i = 0; i <= upto; i++) {
        top.push(xs(i) + "," + ys(hiArr[i]));
        bot.push(xs(i) + "," + ys(loArr[i]));
      }
      return "M " + top.join(" L ") + " L " + bot.reverse().join(" L ") + " Z";
    }

    // Y gridlines for NCLC 4..11.
    var grid = "";
    for (var y = 4; y <= 11; y++) {
      grid += '<line x1="' + xs(0) + '" x2="' + xs(WEEKS) + '" y1="' + ys(y) + '" y2="' + ys(y) + '" class="traj-grid"/>';
      grid += '<text x="' + (PAD.l - 8) + '" y="' + (ys(y) + 4) + '" class="traj-ylabel" text-anchor="end">' + y + '</text>';
    }
    // X labels every 2 weeks.
    var xax = "";
    for (var w = 0; w <= WEEKS; w += 2) {
      xax += '<text x="' + xs(w) + '" y="' + (H - 14) + '" class="traj-xlabel" text-anchor="middle">W' + w + '</text>';
    }
    // Target rule.
    var tgtY = ys(cohort.target);
    var targetRule = '<line x1="' + xs(0) + '" x2="' + xs(WEEKS) + '" y1="' + tgtY + '" y2="' + tgtY + '" class="traj-target"/>' +
                     '<text x="' + (xs(WEEKS) - 4) + '" y="' + (tgtY - 6) + '" class="traj-target-label" text-anchor="end">target NCLC ' + cohort.target + '</text>';

    var bandPath = area(lo, hi, k);
    var medPath = path(med, k);
    var planPath = path(planLine, k);
    var current = '<circle cx="' + xs(k) + '" cy="' + ys(med[k]) + '" r="5" class="traj-dot"/>';

    svg.innerHTML =
      grid + xax + targetRule +
      '<path d="' + bandPath + '" class="traj-band"/>' +
      '<path d="' + planPath + '" class="traj-plan"/>' +
      '<path d="' + medPath + '" class="traj-med"/>' +
      current;

    // Meta panel
    var refusing = cohort.kind === "honest_refusal";
    var rule = cohort.kind === "trivial" ? "trivial" : (refusing ? "honest refusal" : "realistic");
    var ruleClass = refusing ? "status-warn" : "status-ok";
    var meta = document.getElementById("traj-meta");
    meta.innerHTML =
      '<div class="traj-kpi"><span class="kpi-label">Cohort</span><span class="kpi-val">' + cohortReadable(cohort.id) + '</span></div>' +
      '<div class="traj-kpi"><span class="kpi-label">Target</span><span class="kpi-val">NCLC ' + cohort.target + '</span></div>' +
      '<div class="traj-kpi"><span class="kpi-label">Initial min(skill)</span><span class="kpi-val">' + cohort.init.toFixed(1) + '</span></div>' +
      '<div class="traj-kpi"><span class="kpi-label">Week</span><span class="kpi-val">' + k + ' / ' + WEEKS + '</span></div>' +
      '<div class="traj-kpi"><span class="kpi-label">Sim median</span><span class="kpi-val">' + med[k].toFixed(2) + '</span></div>' +
      '<div class="traj-kpi"><span class="kpi-label">Planner</span><span class="kpi-val">' + planLine[k].toFixed(2) + '</span></div>' +
      '<div class="traj-kpi"><span class="kpi-label">P(success)</span><span class="kpi-val">' + (cohort.p * 100).toFixed(0) + '%</span></div>' +
      '<div class="traj-kpi traj-kpi-full"><span class="kpi-label">Planner verdict</span><span class="status-pill ' + ruleClass + '">' + rule + '</span></div>';
  }

  function populateCohorts() {
    var sel = document.getElementById("traj-cohort");
    if (!sel) return;
    COHORTS.forEach(function (c) {
      var opt = document.createElement("option");
      opt.value = c.id;
      var k = c.kind === "honest_refusal" ? "⚠" : c.kind === "trivial" ? "✓" : "●";
      opt.textContent = k + "  " + cohortReadable(c.id) + " → target NCLC " + c.target;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", function () {
      traj.idx = COHORTS.findIndex(function (c) { return c.id === sel.value; });
      traj.week = 0;
      stopTraj();
      renderTrajChart(COHORTS[traj.idx], traj.week);
    });
  }

  function stopTraj() {
    if (traj.anim) {
      clearInterval(traj.anim);
      traj.anim = null;
      var btn = document.getElementById("traj-play");
      if (btn) btn.textContent = "▶ Play 12 weeks";
    }
  }

  function playTraj() {
    stopTraj();
    var btn = document.getElementById("traj-play");
    if (btn) btn.textContent = "❚❚ Pause";
    traj.anim = setInterval(function () {
      traj.week++;
      if (traj.week > WEEKS) {
        traj.week = WEEKS;
        stopTraj();
      } else {
        renderTrajChart(COHORTS[traj.idx], traj.week);
      }
    }, 380);
  }

  if (document.getElementById("traj-chart")) {
    populateCohorts();
    renderTrajChart(COHORTS[0], 0);

    document.getElementById("traj-play").addEventListener("click", function () {
      if (traj.anim) { stopTraj(); return; }
      if (traj.week >= WEEKS) traj.week = 0;
      playTraj();
    });
    document.getElementById("traj-step").addEventListener("click", function () {
      stopTraj();
      traj.week = Math.min(WEEKS, traj.week + 1);
      renderTrajChart(COHORTS[traj.idx], traj.week);
    });
    document.getElementById("traj-reset").addEventListener("click", function () {
      stopTraj();
      traj.week = 0;
      renderTrajChart(COHORTS[traj.idx], traj.week);
    });
  }
})();
