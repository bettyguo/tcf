/*
 * tcf-accel — Practice page.
 * Five real, browser-only French training drills.
 *
 *   ① Diagnostic placement (8 items → per-skill NCLC estimate)
 *   ② SM-2 spaced-repetition vocabulary (240 cards across 5 decks)
 *   ③ Listening dictée (Web Speech TTS + word-level diff)
 *   ④ Timed writing (EE-shape word count + register-coach)
 *   ⑤ Reading speed + comprehension
 *
 * All state in localStorage under the `tcf.practice.*` namespace.
 * No backend, no network, no telemetry.
 */
(function () {
  "use strict";

  /* ───────────────────────────────────────────────────────────
   * Storage helpers
   * ───────────────────────────────────────────────────────── */

  var LS_PREFIX = "tcf.practice.";
  function lsGet(key, fallback) {
    try {
      var v = localStorage.getItem(LS_PREFIX + key);
      return v == null ? fallback : JSON.parse(v);
    } catch (e) { return fallback; }
  }
  function lsSet(key, value) {
    try { localStorage.setItem(LS_PREFIX + key, JSON.stringify(value)); } catch (e) {}
  }
  function lsDel(key) {
    try { localStorage.removeItem(LS_PREFIX + key); } catch (e) {}
  }

  // Streak / minutes tracking — bumped by every tool on each finished session.
  function todayStr() { return new Date().toISOString().slice(0, 10); }
  function markPractice(minutes) {
    var hist = lsGet("history", {});
    var t = todayStr();
    hist[t] = (hist[t] || 0) + Math.max(0, minutes || 0);
    lsSet("history", hist);
    var sessions = lsGet("sessions", 0) + 1;
    lsSet("sessions", sessions);
    renderStreak();
    renderStats();
  }
  function computeStreak() {
    var hist = lsGet("history", {});
    var d = new Date();
    var streak = 0;
    for (var i = 0; i < 730; i++) {
      var key = d.toISOString().slice(0, 10);
      if ((hist[key] || 0) > 0) {
        streak++;
        d.setDate(d.getDate() - 1);
      } else {
        // Allow today to be empty without breaking yesterday's streak.
        if (i === 0) { d.setDate(d.getDate() - 1); continue; }
        break;
      }
    }
    return streak;
  }
  function computeBestStreak() {
    var hist = lsGet("history", {});
    var dates = Object.keys(hist).filter(function (k) { return hist[k] > 0; }).sort();
    if (!dates.length) return 0;
    var best = 1, run = 1;
    for (var i = 1; i < dates.length; i++) {
      var prev = new Date(dates[i - 1]);
      var cur = new Date(dates[i]);
      var diff = Math.round((cur - prev) / 86400000);
      if (diff === 1) { run++; best = Math.max(best, run); }
      else { run = 1; }
    }
    return best;
  }

  function renderStreak() {
    var streak = computeStreak();
    var hist = lsGet("history", {});
    var el = document.querySelector('[data-stat="streak"]');
    if (el) el.textContent = streak;
    var bs = document.querySelector('[data-stat="best-streak"]');
    if (bs) bs.textContent = computeBestStreak();
    var cells = document.querySelector('[data-stat="streak-cells"]');
    if (cells) {
      var html = "";
      var d = new Date();
      d.setDate(d.getDate() - 13);
      for (var i = 0; i < 14; i++) {
        var key = d.toISOString().slice(0, 10);
        var mins = hist[key] || 0;
        var lvl = mins === 0 ? 0 : mins < 5 ? 1 : mins < 15 ? 2 : mins < 30 ? 3 : 4;
        html += '<span class="streak-cell streak-l' + lvl + '" title="' + key + ' — ' + Math.round(mins) + ' min"></span>';
        d.setDate(d.getDate() + 1);
      }
      cells.innerHTML = html;
    }
    var tot = Object.values(hist).reduce(function (a, b) { return a + b; }, 0);
    var totEl = document.querySelector('[data-stat="total-min"]');
    if (totEl) totEl.textContent = Math.round(tot);
    var tot2El = document.querySelector('[data-stat="total-min-2"]');
    if (tot2El) tot2El.textContent = Math.round(tot);
    var sEl = document.querySelector('[data-stat="sessions"]');
    if (sEl) sEl.textContent = lsGet("sessions", 0);
  }

  /* ───────────────────────────────────────────────────────────
   * Web Speech TTS helper
   * ───────────────────────────────────────────────────────── */

  function findFrenchVoice() {
    if (!("speechSynthesis" in window)) return null;
    var voices = window.speechSynthesis.getVoices();
    if (!voices.length) return null;
    // Prefer fr-FR, then fr-CA, then any fr.
    var prio = ["fr-FR", "fr-CA", "fr"];
    for (var i = 0; i < prio.length; i++) {
      var v = voices.find(function (vv) { return (vv.lang || "").toLowerCase().indexOf(prio[i].toLowerCase()) === 0; });
      if (v) return v;
    }
    return null;
  }
  function speak(text, rate, onend) {
    if (!("speechSynthesis" in window)) { onend && onend("no-tts"); return; }
    var voice = findFrenchVoice();
    if (!voice) { onend && onend("no-voice"); return; }
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = rate || 1.0;
    u.pitch = 1.0;
    u.onend = function () { onend && onend(null); };
    u.onerror = function (e) { onend && onend(e.error || "tts-error"); };
    window.speechSynthesis.speak(u);
  }

  // Voices load asynchronously on some platforms — refresh UI when ready.
  if ("speechSynthesis" in window) {
    window.speechSynthesis.onvoiceschanged = function () {
      var btn = document.getElementById("dict-play");
      if (btn && !findFrenchVoice()) {
        btn.disabled = true;
        btn.title = "No French voice installed on this device";
      } else if (btn) {
        btn.disabled = false;
        btn.title = "";
      }
    };
  }

  /* ───────────────────────────────────────────────────────────
   * ① Diagnostic placement
   * ───────────────────────────────────────────────────────── */

  // 8 items, FEI-shape, independently authored.
  // Each item has a difficulty NCLC, a skill, and a correctness rule.
  var DIAG = [
    // CO ×2
    { skill: "CO", nclc: 5, type: "mcq", audio: "Le train pour Lyon part à dix-huit heures quarante-cinq, voie numéro trois.",
      q: "À quelle heure part le train ?", options: ["18 h 15", "18 h 30", "18 h 45", "19 h 00"], correct: 2,
      explain: "« dix-huit heures quarante-cinq » = 18:45." },
    { skill: "CO", nclc: 8, type: "mcq", audio: "Si j'avais su que la réunion serait reportée, je n'aurais pas pris un taxi pour arriver à l'heure.",
      q: "Le locuteur exprime…", options: ["un projet futur", "un regret au passé", "une obligation présente", "une crainte hypothétique"], correct: 1,
      explain: "« j'aurais + participe passé » = conditionnel passé, ici un regret." },
    // CE ×2
    { skill: "CE", nclc: 6, type: "mcq",
      passage: "Le centre communautaire propose des cours de français aux nouveaux arrivants tous les samedis matin, de 9 h à 11 h 30. L'inscription est gratuite mais les places sont limitées à vingt personnes par session.",
      q: "Quelle affirmation est exacte ?",
      options: ["Les cours coûtent 20 dollars.", "Les cours ont lieu le soir.", "L'inscription est gratuite mais les places sont limitées.", "Les cours s'adressent à tous les résidents."],
      correct: 2, explain: "« L'inscription est gratuite mais les places sont limitées à vingt personnes »." },
    { skill: "CE", nclc: 9, type: "mcq",
      passage: "Si la mesure semble aller dans le bon sens, elle n'en demeure pas moins insuffisante face à l'ampleur des défis : sans engagement budgétaire pluriannuel, elle restera lettre morte.",
      q: "L'auteur estime que la mesure est…",
      options: ["pleinement satisfaisante", "bien orientée mais sous-financée", "totalement à rejeter", "techniquement irréalisable"],
      correct: 1, explain: "« semble aller dans le bon sens » (positif) + « sans engagement budgétaire... lettre morte » (insuffisant)." },
    // EE ×2 (self-graded by word count + soft heuristics)
    { skill: "EE", nclc: 6, type: "open", minWords: 60,
      q: "En 60 mots minimum, écris un courriel à un ami pour lui proposer un week-end de randonnée. Précise la date, le lieu, et ce qu'il doit apporter.",
      explain: "Atteindre le mot-cible et nommer les trois éléments (date / lieu / matériel) signale une compétence B1." },
    { skill: "EE", nclc: 8, type: "open", minWords: 120,
      q: "En 120 mots minimum, donne ton point de vue sur la phrase suivante : « Le télétravail isole plus qu'il ne libère. » Justifie avec un argument et un contre-argument.",
      explain: "Position claire + argument + contre-argument + connecteurs (cependant, en revanche, néanmoins) signalent du B2." },
    // EO ×2 (mic optional; if no permission, self-rated)
    { skill: "EO", nclc: 5, type: "speak", seconds: 60,
      q: "Présente-toi en 60 secondes : nom, ville, ce que tu aimes faire le week-end. Parle sans notes.",
      explain: "Un monologue de 60 s sans pauses longues et avec deux idées développées signale B1." },
    { skill: "EO", nclc: 8, type: "speak", seconds: 120,
      q: "En 2 minutes, défends ou rejette : « Les villes devraient interdire les voitures en centre-ville. » Donne deux arguments structurés.",
      explain: "Deux arguments distincts, des connecteurs logiques, et un débit régulier signalent B2." }
  ];

  function startDiag() {
    var state = { i: 0, answers: [], started: Date.now() };
    var intro = document.getElementById("diag-intro");
    var stage = document.getElementById("diag-stage");
    var result = document.getElementById("diag-result");
    intro.hidden = true; stage.hidden = false; result.hidden = true;
    document.getElementById("diag-n").textContent = DIAG.length;
    renderDiagItem(state);

    function next(score) {
      state.answers.push({ skill: DIAG[state.i].skill, nclc: DIAG[state.i].nclc, score: score });
      state.i++;
      if (state.i >= DIAG.length) {
        finishDiag(state);
      } else {
        renderDiagItem(state);
      }
    }
    window._diagNext = next;
  }

  function renderDiagItem(state) {
    var item = DIAG[state.i];
    document.getElementById("diag-i").textContent = state.i + 1;
    document.getElementById("diag-skill").textContent = item.skill + " · " + item.nclc;
    document.getElementById("diag-progress-fg").style.width = ((state.i / DIAG.length) * 100) + "%";

    var box = document.getElementById("diag-item");
    var html = '';
    if (item.type === "mcq") {
      if (item.passage) {
        html += '<blockquote class="diag-passage" lang="fr">' + item.passage + '</blockquote>';
      }
      if (item.audio) {
        html += '<div class="diag-audio"><button class="btn btn-secondary diag-play" type="button">▶ Play (single play)</button><span class="diag-audio-note">CO is single-play in the real exam (ADR-029)</span></div>';
      }
      html += '<p class="diag-q" lang="fr">' + item.q + '</p>';
      html += '<ol class="exam-options diag-opts">';
      item.options.forEach(function (o, i) {
        html += '<li class="exam-opt diag-opt" data-i="' + i + '" tabindex="0" role="button">' +
                '<span class="exam-opt-letter">' + String.fromCharCode(65 + i) + '</span>' +
                '<span lang="fr">' + o + '</span></li>';
      });
      html += '</ol>';
    } else if (item.type === "open") {
      html += '<p class="diag-q" lang="fr">' + item.q + '</p>';
      html += '<textarea class="diag-write" id="diag-write" rows="6" placeholder="Réponds ici…" lang="fr"></textarea>';
      html += '<p class="diag-word-count"><strong id="diag-write-n">0</strong> / ' + item.minWords + ' mots</p>';
      html += '<div class="diag-self">';
      html += '  <p>Auto-grade: ' + item.minWords + '-word minimum. Self-rate clarity after writing.</p>';
      html += '  <button class="btn btn-primary" id="diag-write-submit">Submit my answer</button>';
      html += '</div>';
    } else if (item.type === "speak") {
      html += '<p class="diag-q" lang="fr">' + item.q + '</p>';
      html += '<div class="diag-speak">';
      html += '  <div class="diag-speak-timer" id="diag-speak-timer">' + item.seconds + 's</div>';
      html += '  <div class="diag-speak-controls">';
      html += '    <button class="btn btn-primary" id="diag-speak-start">Start ' + item.seconds + '-second monologue</button>';
      html += '  </div>';
      html += '  <p class="demo-note">Speak out loud. When the timer ends, self-rate your answer below.</p>';
      html += '</div>';
      html += '<div class="diag-self diag-self-rate" hidden id="diag-self-rate">';
      html += '  <p>Self-rate this answer:</p>';
      html += '  <div class="diag-self-buttons">';
      [["1", "Couldn't sustain it"], ["2", "Reached the time, lots of pauses"], ["3", "Got there, some idea-flow"], ["4", "Clear, structured, fluent"]].forEach(function (r) {
        html += '<button class="chip" data-self="' + r[0] + '">' + r[0] + ' — ' + r[1] + '</button>';
      });
      html += '  </div></div>';
    }
    box.innerHTML = html;

    // Wire events for the item just rendered.
    if (item.type === "mcq") {
      if (item.audio) {
        var playBtn = box.querySelector(".diag-play");
        var played = 0;
        playBtn.addEventListener("click", function () {
          if (played >= 1) { playBtn.disabled = true; return; }
          played++;
          speak(item.audio, 1.0, function () { playBtn.disabled = true; });
        });
      }
      box.querySelectorAll(".diag-opt").forEach(function (opt) {
        function pick() {
          var i = parseInt(opt.dataset.i, 10);
          var correct = i === item.correct;
          box.querySelectorAll(".diag-opt").forEach(function (o) { o.classList.add("is-locked"); });
          opt.classList.add(correct ? "is-correct" : "is-wrong");
          var corr = box.querySelector('.diag-opt[data-i="' + item.correct + '"]');
          if (corr) corr.classList.add("is-correct-reveal");
          var ex = document.createElement("p");
          ex.className = "diag-explain";
          ex.innerHTML = (correct ? "✓ " : "✗ ") + item.explain;
          box.appendChild(ex);
          var nxt = document.createElement("button");
          nxt.className = "btn btn-primary diag-next-btn";
          nxt.textContent = (state.i + 1 >= DIAG.length) ? "See my estimate →" : "Next →";
          box.appendChild(nxt);
          nxt.addEventListener("click", function () { window._diagNext(correct ? 1 : 0); });
        }
        opt.addEventListener("click", pick);
        opt.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
      });
    } else if (item.type === "open") {
      var ta = document.getElementById("diag-write");
      var nEl = document.getElementById("diag-write-n");
      ta.addEventListener("input", function () {
        var n = (ta.value.trim().match(/\S+/g) || []).length;
        nEl.textContent = n;
        nEl.style.color = n >= item.minWords ? "var(--success)" : "var(--ink-muted)";
      });
      document.getElementById("diag-write-submit").addEventListener("click", function () {
        var n = (ta.value.trim().match(/\S+/g) || []).length;
        var hit = n >= item.minWords;
        var ex = document.createElement("p");
        ex.className = "diag-explain";
        ex.innerHTML = (hit ? "✓ " : "✗ ") + "Word target " + (hit ? "reached" : "missed") + ". " + item.explain;
        document.getElementById("diag-item").appendChild(ex);
        var nxt = document.createElement("button");
        nxt.className = "btn btn-primary diag-next-btn";
        nxt.textContent = (state.i + 1 >= DIAG.length) ? "See my estimate →" : "Next →";
        document.getElementById("diag-item").appendChild(nxt);
        nxt.addEventListener("click", function () { window._diagNext(hit ? 1 : 0); });
      });
    } else if (item.type === "speak") {
      var startBtn = document.getElementById("diag-speak-start");
      var timer = document.getElementById("diag-speak-timer");
      var rate = document.getElementById("diag-self-rate");
      startBtn.addEventListener("click", function () {
        var remaining = item.seconds;
        timer.textContent = remaining + "s";
        startBtn.disabled = true;
        var t = setInterval(function () {
          remaining--;
          timer.textContent = remaining + "s";
          if (remaining <= 0) {
            clearInterval(t);
            timer.classList.add("is-done");
            timer.textContent = "Time's up";
            rate.hidden = false;
          }
        }, 1000);
      });
      rate.querySelectorAll("[data-self]").forEach(function (b) {
        b.addEventListener("click", function () {
          var v = parseInt(b.dataset.self, 10);
          var s = v >= 3 ? 1 : 0;
          window._diagNext(s);
        });
      });
    }
  }

  function finishDiag(state) {
    var stage = document.getElementById("diag-stage");
    var result = document.getElementById("diag-result");
    stage.hidden = true; result.hidden = false;

    // Per skill: take the higher-level item if correct; otherwise the lower.
    var skills = ["CO", "CE", "EE", "EO"];
    var est = {};
    skills.forEach(function (s) {
      var items = state.answers.filter(function (a) { return a.skill === s; });
      // sort by nclc asc
      items.sort(function (a, b) { return a.nclc - b.nclc; });
      var low = items[0], high = items[1];
      // 4 outcomes:
      //   correct on both → high.nclc + 1 (with wide CI)
      //   correct only on high → high.nclc
      //   correct only on low → midpoint(low, high) − 1
      //   wrong both → low.nclc − 1
      var nclc;
      if (low.score && high.score) nclc = high.nclc + 1;
      else if (high.score) nclc = high.nclc;
      else if (low.score) nclc = Math.round((low.nclc + high.nclc) / 2);
      else nclc = Math.max(3, low.nclc - 1);
      // wide CI: ±2 because n_obs is tiny
      est[s] = { nclc: nclc, lo: Math.max(3, nclc - 2), hi: Math.min(11, nclc + 2) };
    });

    lsSet("diagnostic", { ts: Date.now(), est: est });

    var minutes = Math.max(1, Math.round((Date.now() - state.started) / 60000));
    markPractice(minutes);

    var bottleneck = skills.reduce(function (acc, s) { return est[s].nclc < est[acc].nclc ? s : acc; });
    var html = '';
    html += '<h3>Your screen estimate</h3>';
    html += '<p class="demo-note">8 items is a screen, not a measurement. The intervals below are deliberately wide. The bottleneck skill (<strong>' + bottleneck + '</strong>) is where the planner would put the most minutes.</p>';
    html += '<div class="diag-result-grid">';
    skills.forEach(function (s) {
      var e = est[s];
      var pct = function (v) { return ((Math.max(3, Math.min(11, v)) - 3) / 8) * 100; };
      var isBottle = s === bottleneck;
      html += '<div class="diag-result-skill' + (isBottle ? " is-bottleneck" : "") + '">' +
        '<div class="diag-result-head"><span class="diag-result-skill-name">' + s + '</span>' +
        (isBottle ? '<span class="status-pill status-warn">bottleneck</span>' : '') + '</div>' +
        '<div class="diag-result-num">NCLC ' + e.nclc + '</div>' +
        '<div class="diag-result-ci">95% CI: [' + e.lo + ', ' + e.hi + ']</div>' +
        '<div class="diag-result-bar"><span class="diag-result-bar-ci" style="left:' + pct(e.lo) + '%; width:' + (pct(e.hi) - pct(e.lo)) + '%"></span><span class="diag-result-bar-mark" style="left:' + pct(e.nclc) + '%"></span></div>' +
        '</div>';
    });
    html += '</div>';
    html += '<div class="diag-result-cta">';
    html += '  <p><strong>Suggested next moves:</strong></p>';
    html += '  <ul>';
    html += '    <li>Focus the next two weeks on <strong>' + bottleneck + '</strong> — the ' + (bottleneck === "EE" || bottleneck === "EO" ? "β=" + (bottleneck === "EO" ? "1.5" : "1.4") + " production over-weight" : "reception drills") + ' is documented in <a href="' + (window.SITE_BASE || "") + '/PEDAGOGY/">PEDAGOGY §1</a>.</li>';
    html += '    <li>Use the <a href="#vocab">SRS deck</a> to lift CE/CO ceiling. 240 cards at 10/day = 24 days to full deck.</li>';
    html += '    <li>One <a href="#listening">dictée</a> + one <a href="#writing">writing prompt</a> per day. Production minutes beat passive minutes.</li>';
    html += '  </ul>';
    html += '  <button class="btn btn-secondary" id="diag-retry">Retake placement</button>';
    html += '</div>';
    document.getElementById("diag-result").innerHTML = html;
    document.getElementById("diag-retry").addEventListener("click", function () {
      var intro = document.getElementById("diag-intro");
      intro.hidden = false;
      document.getElementById("diag-result").hidden = true;
    });
    renderStats();
  }

  var diagStartBtn = document.getElementById("diag-start");
  if (diagStartBtn) diagStartBtn.addEventListener("click", startDiag);

  /* ───────────────────────────────────────────────────────────
   * ② SM-2 spaced-repetition vocabulary
   * ───────────────────────────────────────────────────────── */

  // 240 cards organised by deck. fr = front, en = back, ex = example sentence.
  var DECKS = {
    ee_canada: [
      ["la résidence permanente", "permanent residency", "Sa demande de résidence permanente est en cours d'examen."],
      ["déposer une demande", "to file an application", "J'ai déposé ma demande en ligne il y a trois mois."],
      ["accuser réception", "to acknowledge receipt", "Le bureau a accusé réception de mon dossier."],
      ["un délai de traitement", "a processing time", "Le délai de traitement est de huit à douze mois."],
      ["un avis d'invitation", "an invitation to apply", "Elle a reçu un avis d'invitation après deux mois."],
      ["la grille de pointage", "the points grid", "La grille de pointage privilégie les francophones."],
      ["un visa de résident temporaire", "a temporary resident visa", "Il a obtenu un visa de résident temporaire pour étudier."],
      ["la citoyenneté canadienne", "Canadian citizenship", "Trois ans de résidence sont requis pour la citoyenneté canadienne."],
      ["une preuve de fonds", "proof of funds", "Une preuve de fonds suffisants est exigée."],
      ["un casier judiciaire", "a criminal record", "Aucun casier judiciaire ne doit figurer au dossier."],
      ["assermenté", "sworn (translator)", "Tout document doit être traduit par un traducteur assermenté."],
      ["un permis de travail", "a work permit", "Mon permis de travail expire en juin."],
      ["entrer en vigueur", "to come into effect", "La nouvelle politique entre en vigueur lundi."],
      ["un arrêté municipal", "a municipal by-law", "Un arrêté municipal interdit le déneigement sur la voie publique."],
      ["la concertation citoyenne", "citizen consultation", "La mairie organise une concertation citoyenne."],
      ["se prévaloir de", "to avail oneself of", "Vous pouvez vous prévaloir de ce droit jusqu'au 30 juin."],
      ["faire valoir ses droits", "to assert one's rights", "Il a fait valoir ses droits devant le tribunal."],
      ["porter plainte", "to file a complaint", "Vous pouvez porter plainte auprès de l'Ombudsman."],
      ["un recours", "an appeal / remedy", "Plusieurs recours juridiques sont à votre disposition."],
      ["la fonction publique", "the public service", "Il travaille dans la fonction publique fédérale."],
      ["un employeur désigné", "a designated employer", "Vous devez avoir une offre d'un employeur désigné."],
      ["intégrer la société d'accueil", "to integrate into the host society", "Apprendre le français facilite l'intégration à la société d'accueil."],
      ["un nouvel arrivant", "a newcomer", "Le centre accueille les nouveaux arrivants chaque semaine."],
      ["la francisation", "Francization (Quebec)", "Les cours de francisation sont gratuits au Québec."],
      ["le ministère de l'Immigration", "Ministry of Immigration", "Le ministère de l'Immigration a publié de nouvelles directives."],
      ["soumettre des justificatifs", "to submit supporting documents", "Vous devez soumettre des justificatifs financiers."],
      ["se conformer à", "to comply with", "Tous les candidats doivent se conformer aux règles."],
      ["une attestation", "a certificate", "Une attestation de niveau de langue est requise."],
      ["franchir un seuil", "to cross a threshold", "Votre score franchit le seuil minimal."],
      ["s'établir durablement", "to settle permanently", "Ils souhaitent s'établir durablement au Canada."],
      ["le bilinguisme officiel", "official bilingualism", "Le bilinguisme officiel est une politique fédérale."],
      ["une communauté francophone", "a Francophone community", "Une communauté francophone dynamique vit en Alberta."],
      ["un parrainage familial", "family sponsorship", "Le parrainage familial concerne le conjoint et les enfants."],
      ["la mobilité internationale", "international mobility", "Le programme de mobilité internationale est ouvert."],
      ["un séjour temporaire", "a temporary stay", "Son séjour temporaire ne peut excéder six mois."],
      ["la délivrance d'un titre", "issuance of a document", "La délivrance du titre prend de quatre à six semaines."],
      ["en bonne et due forme", "in proper form", "Le dossier doit être présenté en bonne et due forme."],
      ["régulariser sa situation", "to regularize one's status", "Il souhaite régulariser sa situation administrative."],
      ["une infraction au code", "a violation of the code", "Toute infraction au code peut entraîner un refus."],
      ["statuer sur un dossier", "to rule on a case", "L'agent doit statuer sur le dossier sous huit semaines."],
      ["un seuil d'admissibilité", "an eligibility threshold", "Le seuil d'admissibilité a été relevé."],
      ["une cohorte d'admission", "an admission cohort", "La cohorte d'admission de 2026 est plus restreinte."],
      ["s'enraciner", "to take root", "Beaucoup choisissent de s'enraciner dans une ville moyenne."],
      ["le tissu social", "the social fabric", "Les nouveaux arrivants enrichissent le tissu social local."],
      ["l'apprentissage continu", "lifelong learning", "L'apprentissage continu est valorisé sur le marché canadien."],
      ["une instance compétente", "a competent authority", "Adressez-vous à l'instance compétente."],
      ["une formalité administrative", "an administrative formality", "Ce n'est qu'une formalité administrative."],
      ["un parcours d'intégration", "an integration pathway", "Le parcours d'intégration dure jusqu'à trois ans."]
    ],
    work: [
      ["un contrat de travail", "an employment contract", "Le contrat de travail est à durée indéterminée."],
      ["une période d'essai", "a probationary period", "La période d'essai dure trois mois."],
      ["démissionner", "to resign", "Elle a démissionné pour suivre son conjoint."],
      ["être licencié", "to be laid off / fired", "Il a été licencié à la suite d'une restructuration."],
      ["une indemnité de départ", "severance pay", "Son indemnité de départ couvre quatre mois de salaire."],
      ["un entretien d'embauche", "a job interview", "L'entretien d'embauche s'est très bien déroulé."],
      ["une lettre de motivation", "a cover letter", "Soigne ta lettre de motivation, c'est le premier filtre."],
      ["un curriculum vitae", "a résumé / CV", "Mets ton curriculum à jour avant chaque candidature."],
      ["postuler à un poste", "to apply for a position", "J'ai postulé à un poste de chef de projet."],
      ["une fiche de poste", "a job description", "Lis bien la fiche de poste avant l'entretien."],
      ["le salaire brut", "gross salary", "Le salaire brut est de soixante-dix mille par an."],
      ["les charges sociales", "social contributions", "Les charges sociales représentent environ 20 %."],
      ["une augmentation", "a raise", "J'ai obtenu une augmentation de 5 %."],
      ["une promotion", "a promotion", "Elle vise une promotion d'ici la fin de l'année."],
      ["un congé maternité", "maternity leave", "Le congé maternité dure dix-huit semaines."],
      ["un arrêt maladie", "sick leave", "Il est en arrêt maladie depuis lundi."],
      ["télétravailler", "to work remotely", "Nous télétravaillons trois jours par semaine."],
      ["une réunion d'équipe", "a team meeting", "La réunion d'équipe a lieu chaque lundi matin."],
      ["un compte rendu", "minutes / report", "Tu peux rédiger le compte rendu de la réunion ?"],
      ["un ordre du jour", "an agenda", "L'ordre du jour est diffusé la veille."],
      ["un délai serré", "a tight deadline", "Le délai est serré mais tenable."],
      ["respecter une échéance", "to meet a deadline", "Il faut absolument respecter l'échéance du 15."],
      ["une mise en demeure", "a formal notice", "L'avocat a envoyé une mise en demeure."],
      ["la hiérarchie", "the chain of command", "Il faut respecter la hiérarchie dans ce dossier."],
      ["un cadre supérieur", "a senior executive", "Les cadres supérieurs prennent ces décisions."],
      ["un.e collègue de bureau", "an office colleague", "Mes collègues de bureau sont très accueillants."],
      ["un syndicat", "a union", "Le syndicat négocie la nouvelle convention."],
      ["une grève", "a strike", "La grève a duré trois semaines."],
      ["un préavis", "a notice period", "Le préavis est de deux mois pour les cadres."],
      ["un avenant au contrat", "a contract amendment", "Un avenant au contrat formalisera le changement."],
      ["un télétravail occasionnel", "occasional remote work", "Le télétravail occasionnel est toléré, pas un droit."],
      ["un poste à pourvoir", "a vacant position", "Plusieurs postes sont à pourvoir dans l'équipe."],
      ["faire ses preuves", "to prove oneself", "Tu dois encore faire tes preuves cette année."],
      ["mener un projet à bien", "to see a project through", "Elle a mené plusieurs projets à bien sans dépassement."],
      ["livrer dans les temps", "to deliver on time", "L'équipe a livré dans les temps malgré les imprévus."],
      ["un livrable", "a deliverable", "Le livrable de la semaine est le prototype."],
      ["un cahier des charges", "a project brief", "Le cahier des charges est très détaillé."],
      ["s'impliquer pleinement", "to fully commit", "Il s'implique pleinement dans le projet."],
      ["faire valoir son expérience", "to leverage one's experience", "Faites valoir votre expérience à l'international."],
      ["déléguer des tâches", "to delegate tasks", "Apprenez à déléguer pour vous libérer du temps."],
      ["prendre des initiatives", "to take initiative", "Les juniors hésitent à prendre des initiatives."],
      ["faire le point", "to take stock / check in", "Faisons le point en fin de semaine."],
      ["une réunion à distance", "a remote meeting", "La réunion à distance commence à 14 h."],
      ["un emploi du temps chargé", "a busy schedule", "J'ai un emploi du temps chargé cette semaine."],
      ["assurer la continuité", "to ensure continuity", "Le binôme assure la continuité en cas d'absence."],
      ["un changement de cap", "a change of direction", "Ce changement de cap stratégique nous concerne tous."],
      ["décrocher un poste", "to land a job", "Il a décroché un poste chez un grand cabinet."],
      ["un secteur en plein essor", "a booming sector", "L'IA est un secteur en plein essor."],
      ["des compétences transférables", "transferable skills", "Les compétences transférables comptent autant que l'expérience."],
      ["un bilan de compétences", "a skills assessment", "Le bilan de compétences éclaire les choix de carrière."],
      ["un parcours professionnel", "a career path", "Son parcours professionnel est très linéaire."],
      ["mener un entretien", "to conduct an interview", "C'est elle qui mène les entretiens pour ce poste."]
    ],
    school: [
      ["un cursus universitaire", "a university program", "Son cursus universitaire est en sciences politiques."],
      ["une bourse d'études", "a scholarship", "Elle a obtenu une bourse d'études de mérite."],
      ["s'inscrire à un cours", "to register for a class", "Tu peux t'inscrire en ligne dès lundi."],
      ["passer un examen", "to take an exam", "Il passe son examen final demain matin."],
      ["réussir avec mention", "to graduate with honors", "Elle a réussi avec mention très bien."],
      ["échouer à un examen", "to fail an exam", "Il a échoué à l'examen de mi-session."],
      ["un mémoire de fin d'études", "a thesis", "Mon mémoire porte sur la mobilité urbaine."],
      ["soutenir une thèse", "to defend a thesis", "Elle soutient sa thèse vendredi prochain."],
      ["un.e directeur·rice de recherche", "a thesis supervisor", "Son directeur de recherche est très exigeant."],
      ["un séminaire de recherche", "a research seminar", "Le séminaire a lieu tous les jeudis."],
      ["une revue à comité de lecture", "a peer-reviewed journal", "L'article a été publié dans une revue à comité de lecture."],
      ["un échantillon représentatif", "a representative sample", "L'échantillon n'est pas représentatif de la population."],
      ["une hypothèse de travail", "a working hypothesis", "L'hypothèse de travail est partiellement validée."],
      ["étayer un argument", "to back up an argument", "Étaie ton argument avec des données récentes."],
      ["nuancer un propos", "to nuance a statement", "Il faut nuancer ce propos un peu hâtif."],
      ["une démarche analytique", "an analytical approach", "Sa démarche analytique est rigoureuse."],
      ["se documenter sur", "to research a topic", "Documente-toi sur le sujet avant d'écrire."],
      ["citer ses sources", "to cite one's sources", "Cite tes sources dès le brouillon."],
      ["une bibliographie", "a bibliography", "La bibliographie compte cent cinquante références."],
      ["plagier", "to plagiarise", "Plagier entraîne l'exclusion immédiate."],
      ["un travail collaboratif", "collaborative work", "Le travail collaboratif est encouragé en équipe."],
      ["une soutenance orale", "an oral defense", "La soutenance orale dure trente minutes."],
      ["un diplôme universitaire", "a university degree", "Son diplôme universitaire est reconnu au Canada."],
      ["une équivalence de diplôme", "a degree equivalency", "L'équivalence de diplôme prend trois à six mois."],
      ["un programme d'échange", "an exchange program", "Elle part en programme d'échange à Montréal."],
      ["la rentrée scolaire", "back-to-school season", "La rentrée scolaire approche."],
      ["des frais de scolarité", "tuition fees", "Les frais de scolarité ont augmenté de 3 %."],
      ["réviser un examen", "to revise for an exam", "Je révise mes examens depuis deux semaines."],
      ["un fascicule de cours", "a course handout", "Le fascicule de cours est disponible en PDF."],
      ["un travail noté", "a graded assignment", "Le travail noté compte pour 30 % de la note finale."],
      ["la moyenne pondérée", "the weighted average", "La moyenne pondérée est de 14,2."],
      ["un coefficient de pondération", "a weighting coefficient", "Le coefficient de pondération est de 2."],
      ["une lecture obligatoire", "required reading", "Les lectures obligatoires sont précisées au syllabus."],
      ["un exposé oral", "an oral presentation", "Mon exposé oral porte sur la francophonie nord-américaine."],
      ["une fiche de lecture", "a reading note", "La fiche de lecture résume l'argument principal."],
      ["une dissertation argumentée", "an argumentative essay", "La dissertation argumentée fait 1500 mots."],
      ["une problématique", "a research question", "Formule clairement ta problématique."],
      ["une étude de cas", "a case study", "L'étude de cas illustre la théorie."],
      ["la rentrée en master", "starting a master's", "La rentrée en master se fait en septembre."]
    ],
    daily: [
      ["faire les courses", "to do the shopping", "Je fais les courses tous les samedis."],
      ["payer comptant", "to pay cash", "On peut payer comptant ou par carte."],
      ["régler la facture", "to settle the bill", "Tu peux régler la facture en ligne."],
      ["un relevé bancaire", "a bank statement", "Mon relevé bancaire arrive le 1er du mois."],
      ["un prélèvement automatique", "a direct debit", "Le loyer est en prélèvement automatique."],
      ["un découvert autorisé", "an overdraft facility", "Le découvert autorisé est de 500 dollars."],
      ["faire un virement", "to make a transfer", "Je vais faire un virement ce soir."],
      ["une mutuelle santé", "supplementary health insurance", "Sans mutuelle santé, les soins coûtent cher."],
      ["une ordonnance médicale", "a prescription", "Le médecin m'a fait une ordonnance."],
      ["prendre rendez-vous", "to make an appointment", "Je vais prendre rendez-vous chez le dentiste."],
      ["un bilan de santé", "a check-up", "Le bilan de santé annuel est gratuit."],
      ["un arrêt de bus", "a bus stop", "L'arrêt de bus est juste devant chez moi."],
      ["une carte de transport", "a transit pass", "La carte de transport mensuelle coûte 95 dollars."],
      ["faire le plein", "to fill up (gas)", "Je dois faire le plein avant l'autoroute."],
      ["un permis de conduire", "a driver's licence", "Mon permis de conduire est valable cinq ans."],
      ["payer son loyer", "to pay rent", "Je paie mon loyer en début de mois."],
      ["un bail de location", "a lease", "Le bail est de douze mois renouvelable."],
      ["un dépôt de garantie", "a security deposit", "Le dépôt de garantie correspond à un mois."],
      ["un état des lieux", "a walkthrough inventory", "L'état des lieux se fait à l'entrée et à la sortie."],
      ["une réparation locative", "a tenant repair", "Les réparations locatives sont à la charge du locataire."],
      ["assurer son logement", "to insure one's home", "Vous devez assurer votre logement."],
      ["un quartier résidentiel", "a residential neighborhood", "C'est un quartier résidentiel très calme."],
      ["déménager", "to move out", "Je déménage à la fin du mois."],
      ["emménager", "to move in", "Nous emménageons dans deux semaines."],
      ["faire la lessive", "to do the laundry", "Je fais la lessive le dimanche."],
      ["ranger l'appartement", "to tidy up", "Range l'appartement avant que les invités arrivent."],
      ["faire des économies", "to save money", "Je fais des économies pour un voyage."],
      ["serrer son budget", "to tighten one's budget", "Je dois serrer mon budget ce mois-ci."],
      ["un imprévu", "an unforeseen event", "Un imprévu a chamboulé mes plans."],
      ["recevoir un colis", "to receive a parcel", "J'ai reçu un colis ce matin."],
      ["un suivi de livraison", "a delivery tracking", "Le suivi de livraison indique demain matin."],
      ["se renseigner sur", "to inquire about", "Renseigne-toi sur les horaires."],
      ["un service après-vente", "customer service / SAV", "Le service après-vente ne répond pas."],
      ["faire une réclamation", "to make a complaint", "J'ai fait une réclamation par écrit."],
      ["un remboursement intégral", "a full refund", "Ils proposent un remboursement intégral."],
      ["un fichier à signer", "a document to sign", "Vous recevrez un fichier à signer par mail."],
      ["une signature électronique", "an e-signature", "La signature électronique a valeur légale."],
      ["souscrire un abonnement", "to take out a subscription", "Je vais souscrire un abonnement gym."],
      ["résilier un contrat", "to cancel a contract", "Je veux résilier mon contrat d'électricité."],
      ["un délai de rétractation", "a cooling-off period", "Vous avez un délai de rétractation de 14 jours."],
      ["une carte d'assurance maladie", "a health insurance card", "Présentez votre carte d'assurance maladie."],
      ["des frais médicaux", "medical fees", "Les frais médicaux sont partiellement couverts."],
      ["consulter un spécialiste", "to see a specialist", "Tu devrais consulter un spécialiste."],
      ["un médecin de famille", "a family doctor", "Trouver un médecin de famille n'est pas facile."],
      ["un effet secondaire", "a side effect", "Ce médicament a peu d'effets secondaires."],
      ["se mettre au vert", "to escape to the country", "On part se mettre au vert ce week-end."],
      ["faire le tri", "to sort through", "Je fais le tri dans mes affaires."],
      ["la collecte sélective", "selective recycling", "La collecte sélective a lieu le mardi."],
      ["un geste écoresponsable", "an eco-friendly gesture", "Refuser le sac plastique est un geste écoresponsable."],
      ["un mode de vie sain", "a healthy lifestyle", "Un mode de vie sain réduit les coûts médicaux."],
      ["faire face à un imprévu", "to deal with the unexpected", "Mon épargne me permet de faire face à un imprévu."],
      ["un dossier à compléter", "a file to complete", "Il manque deux pièces à compléter dans le dossier."],
      ["souscrire une assurance", "to take out insurance", "Souscrivez une assurance avant le départ."],
      ["une attestation d'hébergement", "a host certificate", "Une attestation d'hébergement est requise."],
      ["régler en plusieurs fois", "to pay in installments", "Vous pouvez régler en trois fois sans frais."],
      ["faire suivre son courrier", "to forward one's mail", "J'ai fait suivre mon courrier à la nouvelle adresse."],
      ["souscrire en ligne", "to sign up online", "Vous pouvez souscrire en ligne en cinq minutes."],
      ["un service à la clientèle", "customer service (Quebec)", "Le service à la clientèle ouvre à 9 h."],
      ["une carte de débit", "a debit card", "Je paye toujours par carte de débit."],
      ["un revenu net mensuel", "net monthly income", "Mon revenu net mensuel couvre les dépenses fixes."],
      ["un crédit à la consommation", "a consumer loan", "Évitez les crédits à la consommation à taux élevés."],
      ["un trop-perçu", "an overpayment", "L'organisme réclame le remboursement d'un trop-perçu."]
    ],
    connectors: [
      ["d'une part… d'autre part", "on the one hand… on the other", "D'une part le coût, d'autre part le délai."],
      ["en revanche", "on the other hand", "Le prix est élevé ; en revanche, la qualité est exceptionnelle."],
      ["néanmoins", "nevertheless", "L'idée est séduisante ; néanmoins, elle reste irréalisable."],
      ["toutefois", "however", "Toutefois, les chiffres récents nuancent ce constat."],
      ["cependant", "however", "Cependant, plusieurs voix s'élèvent contre ce projet."],
      ["par conséquent", "consequently", "Par conséquent, la décision a été reportée."],
      ["ainsi", "thus / hence", "Ainsi, deux options s'offrent à nous."],
      ["dès lors", "from then on / thus", "Dès lors, il n'est plus possible de reculer."],
      ["du fait que", "owing to the fact that", "Du fait que les délais sont serrés, nous accélérons."],
      ["étant donné que", "given that", "Étant donné que la loi a changé, le calcul varie."],
      ["dans la mesure où", "insofar as", "Dans la mesure où vous acceptez la clause, c'est faisable."],
      ["sous prétexte que", "on the pretext that", "Il refuse sous prétexte que c'est trop cher."],
      ["à supposer que", "supposing that", "À supposer que ce soit vrai, que faire ?"],
      ["pour peu que", "as long as", "Pour peu que tu acceptes, on commence demain."],
      ["bien que", "although (+ subj.)", "Bien qu'il pleuve, je sors quand même."],
      ["quoique", "even though (+ subj.)", "Quoique fatigué, il a tenu sa promesse."],
      ["en dépit de", "despite", "En dépit des avertissements, il est parti."],
      ["malgré tout", "despite everything", "Malgré tout, le projet avance."],
      ["si bien que", "so much so that", "Il a tellement insisté si bien qu'elle a cédé."],
      ["au point que", "to the point that", "Le silence dure au point que c'en est gênant."],
      ["à tel point que", "to such an extent that", "Le climat se dégrade à tel point que la sécheresse s'installe."],
      ["en somme", "in short", "En somme, le bilan est mitigé."],
      ["pour résumer", "to sum up", "Pour résumer, trois axes se dégagent."],
      ["en définitive", "ultimately", "En définitive, la stratégie reste à définir."],
      ["force est de constater que", "one has to admit that", "Force est de constater que la situation a empiré."],
      ["il n'en demeure pas moins que", "the fact remains that", "Il n'en demeure pas moins que les efforts sont insuffisants."],
      ["en outre", "moreover", "En outre, le coût total dépasse le budget."],
      ["de surcroît", "furthermore", "De surcroît, les délais se sont allongés."],
      ["qui plus est", "what is more", "Qui plus est, le rapport est attendu lundi."],
      ["autrement dit", "in other words", "Autrement dit, il faut tout reprendre."],
      ["c'est-à-dire", "that is to say", "Un cycle complet, c'est-à-dire douze semaines."],
      ["à savoir", "namely", "Trois critères, à savoir le coût, la durée et la qualité."],
      ["en l'occurrence", "in this case", "En l'occurrence, la solution est simple."],
      ["en revanche", "by contrast", "En revanche, les ventes augmentent à l'étranger."],
      ["par ailleurs", "moreover", "Par ailleurs, le calendrier est tendu."],
      ["pour autant", "even so", "Pour autant, rien n'est joué."],
      ["loin de", "far from", "Loin de calmer la situation, ces mesures l'ont aggravée."],
      ["en l'état actuel", "as things stand", "En l'état actuel, aucune décision n'est prise."],
      ["dans la même veine", "in the same vein", "Dans la même veine, on peut citer ce rapport."],
      ["paradoxalement", "paradoxically", "Paradoxalement, la mesure produit l'effet inverse."]
    ]
  };
  // Build "all" deck by tagging each card with deckId.
  var ALL_DECK = [];
  Object.keys(DECKS).forEach(function (deckId) {
    DECKS[deckId].forEach(function (c, i) {
      ALL_DECK.push({ id: deckId + ":" + i, deck: deckId, fr: c[0], en: c[1], ex: c[2] || "" });
    });
  });

  // SM-2 state per card id: { ease, interval, reps, due (ms) }
  function srsLoad() { return lsGet("srs", {}); }
  function srsSave(s) { lsSet("srs", s); }
  function srsCardState(cards, deckFilter) {
    var pool = deckFilter === "all" ? cards : cards.filter(function (c) { return c.deck === deckFilter; });
    var s = srsLoad();
    var now = Date.now();
    var due = [], fresh = [], learned = [];
    pool.forEach(function (c) {
      var st = s[c.id];
      if (!st) fresh.push(c);
      else if (st.due <= now) due.push(c);
      else learned.push(c);
    });
    return { due: due, fresh: fresh, learned: learned };
  }
  function sm2(state, q) {
    // q 1..5 (1=fail). SuperMemo SM-2.
    if (!state) state = { ease: 2.5, interval: 0, reps: 0 };
    if (q < 3) {
      state.reps = 0;
      state.interval = q === 1 ? 1 : Math.max(1, Math.round(state.interval / 2));
    } else {
      if (state.reps === 0) state.interval = 1;
      else if (state.reps === 1) state.interval = 3;
      else state.interval = Math.round(state.interval * state.ease);
      state.reps++;
    }
    state.ease = Math.max(1.3, state.ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
    state.due = Date.now() + state.interval * 86400000;
    state.lastQ = q;
    return state;
  }
  function srsUpdateCounters(deck) {
    var s = srsCardState(ALL_DECK, deck);
    var dueEl = document.querySelector('[data-srs="due"]');
    var newEl = document.querySelector('[data-srs="new"]');
    var lEl = document.querySelector('[data-srs="learned"]');
    if (dueEl) dueEl.textContent = s.due.length;
    if (newEl) newEl.textContent = s.fresh.length;
    if (lEl) lEl.textContent = s.learned.length;
  }
  function srsDirection() {
    var r = document.querySelector('input[name="srs-dir"]:checked');
    return r ? r.value : "fr2en";
  }
  function srsCurrentDeck() {
    var el = document.getElementById("srs-deck");
    return el ? el.value : "all";
  }
  var srsState = { card: null, started: 0, revealed: false };

  function srsNext() {
    var deck = srsCurrentDeck();
    var s = srsCardState(ALL_DECK, deck);
    // Prefer due (review), then fresh (new), interleaving 4:1.
    var pickFromFresh = s.due.length === 0 || (s.fresh.length > 0 && Math.random() < 0.2);
    var card = pickFromFresh ? s.fresh[Math.floor(Math.random() * s.fresh.length)] : s.due[Math.floor(Math.random() * s.due.length)];
    if (!card && s.learned.length) card = s.learned[Math.floor(Math.random() * s.learned.length)];
    srsState.card = card;
    srsState.revealed = false;
    if (!srsState.started) srsState.started = Date.now();
    srsRender();
  }
  function srsRender() {
    var stage = document.getElementById("srs-stage");
    if (!stage) return;
    var card = srsState.card;
    if (!card) {
      stage.innerHTML = '<p class="srs-empty">All caught up. Come back tomorrow — the algorithm will schedule new reviews.</p>';
      return;
    }
    var dir = srsDirection();
    var front = dir === "fr2en" ? card.fr : card.en;
    var back = dir === "fr2en" ? card.en : card.fr;
    var html = '';
    html += '<div class="srs-card-inner">';
    html += '  <div class="srs-card-front" lang="' + (dir === "fr2en" ? "fr" : "en") + '">';
    html += '    <p class="srs-card-text">' + front + '</p>';
    if ("speechSynthesis" in window && card.fr) {
      html += '    <button class="srs-tts" type="button" aria-label="Hear French">🔊 Hear</button>';
    }
    html += '  </div>';
    if (srsState.revealed) {
      html += '  <div class="srs-card-back">';
      html += '    <p class="srs-card-text" lang="' + (dir === "fr2en" ? "en" : "fr") + '">' + back + '</p>';
      if (card.ex) html += '<p class="srs-card-ex" lang="fr"><em>' + card.ex + '</em></p>';
      html += '  </div>';
      html += '  <div class="srs-rate">';
      [["1", "Blackout"], ["2", "Wrong"], ["3", "Hard"], ["4", "OK"], ["5", "Easy"]].forEach(function (r) {
        html += '<button class="srs-rate-btn srs-r' + r[0] + '" data-q="' + r[0] + '">' + r[0] + '<span>' + r[1] + '</span></button>';
      });
      html += '  </div>';
    } else {
      html += '  <button class="btn btn-primary srs-reveal" type="button">Reveal answer (space)</button>';
    }
    html += '</div>';
    stage.innerHTML = html;
    var revealBtn = stage.querySelector(".srs-reveal");
    if (revealBtn) revealBtn.addEventListener("click", function () { srsState.revealed = true; srsRender(); });
    var ttsBtn = stage.querySelector(".srs-tts");
    if (ttsBtn) ttsBtn.addEventListener("click", function () { speak(card.fr, 1.0); });
    stage.querySelectorAll(".srs-rate-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        var q = parseInt(b.dataset.q, 10);
        var s = srsLoad();
        s[card.id] = sm2(s[card.id], q);
        srsSave(s);
        srsUpdateCounters(srsCurrentDeck());
        srsNext();
      });
    });
  }
  // Keyboard: space = reveal, 1..5 = rate.
  document.addEventListener("keydown", function (e) {
    if (!document.querySelector(".srs-card")) return;
    var stage = document.getElementById("srs-stage");
    if (!stage || !document.activeElement) return;
    if (document.activeElement.tagName === "TEXTAREA" || document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "SELECT") return;
    if (e.key === " " && !srsState.revealed && srsState.card) { e.preventDefault(); srsState.revealed = true; srsRender(); }
    else if (srsState.revealed && /^[1-5]$/.test(e.key)) {
      var btn = stage.querySelector('.srs-rate-btn[data-q="' + e.key + '"]');
      if (btn) btn.click();
    }
  });

  if (document.getElementById("srs-stage")) {
    document.getElementById("srs-deck").addEventListener("change", function () {
      srsUpdateCounters(srsCurrentDeck());
      srsNext();
    });
    document.querySelectorAll('input[name="srs-dir"]').forEach(function (r) {
      r.addEventListener("change", srsRender);
    });
    srsUpdateCounters(srsCurrentDeck());
    srsNext();
    // Mark practice when leaving srs session (5+ cards reviewed).
    window.addEventListener("beforeunload", function () {
      if (srsState.started) {
        var mins = Math.round((Date.now() - srsState.started) / 60000);
        if (mins > 0) markPractice(mins);
      }
    });
  }

  /* ───────────────────────────────────────────────────────────
   * ③ Listening dictée
   * ───────────────────────────────────────────────────────── */

  var DICTEES = {
    A2: [
      "Bonjour, je voudrais réserver une table pour quatre personnes, vendredi soir, vers vingt heures.",
      "Le bureau ferme à dix-sept heures et rouvre lundi à neuf heures du matin.",
      "Je cherche la station de métro la plus proche, s'il vous plaît.",
      "Le colis sera livré demain entre treize et seize heures.",
      "Quel est votre numéro de téléphone, monsieur ?"
    ],
    B1: [
      "Il faut absolument confirmer le rendez-vous avant mardi, sinon la place sera reprise.",
      "La conférence aura lieu en ligne le quinze juin, à partir de quatorze heures précises.",
      "Si vous n'avez pas reçu votre carte d'ici la fin du mois, contactez immédiatement le service client.",
      "Les inscriptions ouvrent le premier septembre et se terminent le quinze octobre.",
      "Pour des raisons techniques, le service de paiement en ligne est temporairement interrompu."
    ],
    B2: [
      "Le rapport annuel souligne une amélioration sensible des résultats malgré un contexte économique défavorable.",
      "Bien que les négociations aient duré plusieurs mois, aucun accord définitif n'a pu être trouvé.",
      "Les autorités sanitaires recommandent vivement la vaccination annuelle pour les personnes vulnérables.",
      "Cette décision, prise à la majorité absolue, entrera en vigueur dès le premier janvier prochain.",
      "Force est de constater que le dispositif actuel ne répond plus aux besoins de la population."
    ],
    C1: [
      "L'enjeu, dès lors, n'est plus tant la faisabilité technique que l'acceptabilité sociale de la réforme proposée.",
      "On aurait tort de croire que ces évolutions, aussi profondes soient-elles, échappent au pouvoir des élus.",
      "Loin d'apaiser les tensions, l'annonce gouvernementale les a au contraire ravivées, suscitant un tollé général.",
      "Quoique séduisante en apparence, cette proposition se heurte à des obstacles juridiques considérables.",
      "Il n'en demeure pas moins que la transition énergétique ne saurait se faire sans concertation préalable."
    ]
  };

  var dictState = { passage: null, plays: 0 };

  function dictPickPassage() {
    var lvl = document.getElementById("dict-level").value;
    var pool = DICTEES[lvl];
    dictState.passage = pool[Math.floor(Math.random() * pool.length)];
    dictState.plays = 0;
    document.getElementById("dict-input").value = "";
    document.getElementById("dict-result").hidden = true;
    document.getElementById("dict-replay").disabled = true;
    document.getElementById("dict-meta").textContent = "Words: 0 · Audio plays: 0";
  }
  function dictPlay(penalised) {
    if (!dictState.passage) dictPickPassage();
    var rate = parseFloat(document.getElementById("dict-rate").value);
    speak(dictState.passage, rate, function (err) {
      if (err === "no-tts" || err === "no-voice") {
        var btn = document.getElementById("dict-play");
        btn.disabled = true;
        btn.title = "No French TTS available on this device";
        alert("French text-to-speech isn't available here. Install a French voice in your OS settings.");
      }
    });
    dictState.plays++;
    document.getElementById("dict-replay").disabled = false;
    var meta = document.getElementById("dict-meta");
    var n = (document.getElementById("dict-input").value.trim().match(/\S+/g) || []).length;
    meta.textContent = "Words: " + n + " · Audio plays: " + dictState.plays + (penalised ? " (replay)" : "");
  }

  // Simple word-level diff (Levenshtein on tokens).
  function normWord(w) {
    return (w || "").toLowerCase()
      .replace(/[.,;:!?«»"'()…—–]/g, "")
      .normalize("NFD").replace(/[̀-ͯ]/g, ""); // strip diacritics for matching
  }
  function diffTokens(a, b) {
    // a, b are arrays of words. Returns operations [type, aWord, bWord].
    var m = a.length, n = b.length;
    var dp = [];
    for (var i = 0; i <= m; i++) { dp.push(new Array(n + 1)); dp[i][0] = i; }
    for (var j = 0; j <= n; j++) dp[0][j] = j;
    for (i = 1; i <= m; i++) {
      for (j = 1; j <= n; j++) {
        var cost = normWord(a[i - 1]) === normWord(b[j - 1]) ? 0 : 1;
        dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost);
      }
    }
    var ops = []; i = m; j = n;
    while (i > 0 || j > 0) {
      if (i > 0 && j > 0 && normWord(a[i - 1]) === normWord(b[j - 1])) {
        var exact = a[i - 1] === b[j - 1];
        ops.unshift([exact ? "ok" : "diacritic", a[i - 1], b[j - 1]]);
        i--; j--;
      } else if (i > 0 && j > 0 && dp[i][j] === dp[i - 1][j - 1] + 1) {
        ops.unshift(["sub", a[i - 1], b[j - 1]]); i--; j--;
      } else if (j > 0 && (i === 0 || dp[i][j] === dp[i][j - 1] + 1)) {
        ops.unshift(["add", null, b[j - 1]]); j--;
      } else {
        ops.unshift(["del", a[i - 1], null]); i--;
      }
    }
    return ops;
  }
  function dictCheck() {
    if (!dictState.passage) return;
    var truth = dictState.passage;
    var user = (document.getElementById("dict-input").value || "").trim();
    var truthTokens = truth.split(/\s+/);
    var userTokens = user.split(/\s+/);
    var ops = diffTokens(userTokens, truthTokens);
    var html = '<h4>Result</h4>';
    var ok = 0, total = truthTokens.length;
    var diffHtml = '';
    ops.forEach(function (o) {
      if (o[0] === "ok") { diffHtml += '<span class="diff-ok">' + (o[1] || "") + '</span> '; ok++; }
      else if (o[0] === "diacritic") { diffHtml += '<span class="diff-diacritic" title="Accent/case off: expected ' + (o[2] || "") + '">' + (o[1] || "") + '</span> '; ok += 0.7; }
      else if (o[0] === "sub") { diffHtml += '<span class="diff-sub" title="Expected: ' + (o[2] || "") + '">' + (o[1] || "?") + '</span> '; }
      else if (o[0] === "del") { diffHtml += '<span class="diff-del">' + (o[1] || "") + '</span> '; }
      else if (o[0] === "add") { diffHtml += '<span class="diff-add" title="Missed">' + (o[2] || "") + '</span> '; }
    });
    var pct = Math.round((ok / Math.max(1, total)) * 100);
    var hist = lsGet("dict-history", []);
    hist.push({ ts: Date.now(), level: document.getElementById("dict-level").value, pct: pct, plays: dictState.plays });
    lsSet("dict-history", hist.slice(-100));

    html += '<div class="dict-score">Score: <strong>' + pct + '%</strong> · ' + Math.round(ok * 10) / 10 + ' / ' + total + ' words · plays: ' + dictState.plays + '</div>';
    html += '<p class="dict-truth-label">Target passage</p>';
    html += '<p class="dict-truth" lang="fr">' + truth + '</p>';
    html += '<p class="dict-diff-label">Your transcription, word-graded</p>';
    html += '<p class="dict-diff" lang="fr">' + diffHtml + '</p>';
    html += '<div class="dict-legend"><span class="diff-ok">exact</span> · <span class="diff-diacritic">accent/case</span> · <span class="diff-sub">wrong</span> · <span class="diff-add">missed</span></div>';
    var rb = document.getElementById("dict-result");
    rb.innerHTML = html;
    rb.hidden = false;
    markPractice(2);
  }

  if (document.getElementById("dict-play")) {
    document.getElementById("dict-play").addEventListener("click", function () { dictPickPassage(); dictPlay(false); });
    document.getElementById("dict-replay").addEventListener("click", function () { dictPlay(true); });
    document.getElementById("dict-skip").addEventListener("click", function () { dictPickPassage(); });
    document.getElementById("dict-check").addEventListener("click", dictCheck);
    var dictInput = document.getElementById("dict-input");
    dictInput.addEventListener("input", function () {
      var n = (dictInput.value.trim().match(/\S+/g) || []).length;
      document.getElementById("dict-meta").textContent = "Words: " + n + " · Audio plays: " + dictState.plays;
    });
    dictInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); dictCheck(); }
    });
    // Check voice availability initially.
    if ("speechSynthesis" in window) {
      setTimeout(function () {
        if (!findFrenchVoice()) {
          var btn = document.getElementById("dict-play");
          btn.disabled = true;
          btn.title = "No French voice on this device — install one in OS settings";
        }
      }, 500);
    }
  }

  /* ───────────────────────────────────────────────────────────
   * ④ Timed writing
   * ───────────────────────────────────────────────────────── */

  var WRITE_PROMPTS = {
    T1: [
      "Écris un courriel à ton voisin pour lui proposer de garder ton chat pendant tes vacances. Précise les dates et les soins nécessaires. (≥60 mots)",
      "Tu invites une amie à un événement culturel à Montréal. Précise le lieu, l'heure et pourquoi tu y vas. (≥60 mots)",
      "Tu écris à un service de location pour signaler un problème dans ton appartement. Sois clair et poli. (≥60 mots)",
      "Tu confirmes un rendez-vous par message à ton dentiste, mais tu demandes un autre créneau. (≥60 mots)",
      "Tu écris à un collègue pour lui expliquer pourquoi tu seras absent.e demain. (≥60 mots)"
    ],
    T2: [
      "Raconte une journée de bénévolat à laquelle tu as participé : ce que tu as fait, ce que tu as appris. (≥120 mots)",
      "Décris un voyage qui a changé ta façon de voir une culture. Donne deux exemples concrets. (≥120 mots)",
      "Rends compte d'un événement (festival, conférence, manifestation) auquel tu as assisté récemment. (≥120 mots)",
      "Raconte une expérience professionnelle marquante et ce qu'elle t'a appris. (≥120 mots)",
      "Décris ton quartier idéal pour ta famille dans cinq ans : éléments concrets et raison. (≥120 mots)"
    ],
    T3: [
      "« Le télétravail isole plus qu'il ne libère. » Donne ton point de vue, avec un argument et un contre-argument. (≥180 mots)",
      "« Les villes devraient interdire les voitures en centre-ville. » Discute en utilisant deux arguments structurés. (≥180 mots)",
      "« L'apprentissage en ligne ne remplacera jamais la salle de classe. » Position personnelle + nuances. (≥180 mots)",
      "« Voyager forme la jeunesse — mais à quel prix écologique ? » Position personnelle nuancée. (≥180 mots)",
      "« Les réseaux sociaux nuisent au débat démocratique. » Pour ou contre, avec contre-argument. (≥180 mots)",
      "« Il vaut mieux étudier dans son pays natal que partir à l'étranger. » Discute. (≥180 mots)"
    ]
  };
  var WRITE_TARGETS = { T1: { words: 60, minutes: 8 }, T2: { words: 120, minutes: 20 }, T3: { words: 180, minutes: 32 } };

  var wState = { task: "T3", prompt: "", started: 0, remaining: 32 * 60, timer: null };

  function wNewPrompt() {
    wState.task = document.getElementById("write-task").value;
    var pool = WRITE_PROMPTS[wState.task];
    wState.prompt = pool[Math.floor(Math.random() * pool.length)];
    document.getElementById("write-prompt").textContent = wState.prompt;
    document.getElementById("write-target").textContent = WRITE_TARGETS[wState.task].words;
    wState.remaining = WRITE_TARGETS[wState.task].minutes * 60;
    wRenderTime();
    document.getElementById("write-textarea").value = "";
    wRecount();
  }
  function wRenderTime() {
    var m = Math.floor(wState.remaining / 60), s = wState.remaining % 60;
    document.getElementById("write-time").textContent = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }
  function wRecount() {
    var txt = document.getElementById("write-textarea").value;
    var words = (txt.trim().match(/\S+/g) || []).length;
    var sentences = (txt.match(/[.!?]+(?=\s|$)/g) || []).length;
    var lower = txt.toLowerCase().match(/[a-zà-ÿ]+/gi) || [];
    var uniq = new Set(lower).size;
    var unqPct = lower.length ? Math.round((uniq / lower.length) * 100) : 0;
    document.getElementById("write-words").textContent = words;
    document.getElementById("write-sent").textContent = sentences;
    document.getElementById("write-unique").textContent = unqPct;
    var target = WRITE_TARGETS[wState.task].words;
    document.getElementById("write-words").style.color = words >= target ? "var(--success)" : "var(--ink)";
    // Live hints
    var hints = [];
    if (words < Math.round(target * 0.3)) hints.push("Encore loin du minimum — vise au moins " + target + " mots.");
    else if (words < target) hints.push("Tu approches : il manque " + (target - words) + " mots pour atteindre le minimum (pénalité déterministe sinon).");
    else hints.push("✓ Minimum atteint (" + words + " / " + target + ").");
    var connectors = ["cependant", "néanmoins", "en revanche", "par conséquent", "toutefois", "ainsi", "en outre", "par ailleurs", "d'autre part", "d'une part", "en somme", "bien que"];
    var hasConn = connectors.some(function (c) { return txt.toLowerCase().indexOf(c) >= 0; });
    if (wState.task === "T3" && !hasConn && words > 50) hints.push("Aucun connecteur logique détecté (cependant / en revanche / par conséquent…). T3 exige une argumentation structurée.");
    if (wState.task === "T3" && sentences > 0 && sentences < 4 && words > 80) hints.push("Peu de phrases (" + sentences + ") pour une argumentation — sois plus segmenté.");
    if (unqPct && unqPct < 45 && words > 60) hints.push("Diversité lexicale faible (" + unqPct + "% mots uniques). Tu te répètes.");
    if (words > target * 1.5) hints.push("Tu dépasses largement la cible. Si c'est un brouillon, OK ; sinon, raccourcis.");
    var ul = document.getElementById("write-hints");
    ul.innerHTML = hints.map(function (h) { return "<li>" + h + "</li>"; }).join("");
  }
  function wStart() {
    if (wState.timer) clearInterval(wState.timer);
    wState.started = Date.now();
    wState.timer = setInterval(function () {
      wState.remaining = Math.max(0, wState.remaining - 1);
      wRenderTime();
      if (wState.remaining <= 0) {
        clearInterval(wState.timer); wState.timer = null;
        document.getElementById("write-textarea").disabled = true;
        var c = lsGet("write-count", 0) + 1;
        lsSet("write-count", c);
        markPractice(WRITE_TARGETS[wState.task].minutes);
      }
    }, 1000);
    document.getElementById("write-textarea").focus();
  }
  function wReset() {
    if (wState.timer) { clearInterval(wState.timer); wState.timer = null; }
    wState.remaining = WRITE_TARGETS[wState.task].minutes * 60;
    document.getElementById("write-textarea").disabled = false;
    document.getElementById("write-textarea").value = "";
    wRenderTime(); wRecount();
  }

  if (document.getElementById("write-textarea")) {
    document.getElementById("write-task").addEventListener("change", function () { wNewPrompt(); wReset(); });
    document.getElementById("write-newprompt").addEventListener("click", wNewPrompt);
    document.getElementById("write-start").addEventListener("click", wStart);
    document.getElementById("write-reset").addEventListener("click", wReset);
    document.getElementById("write-textarea").addEventListener("input", wRecount);
    wNewPrompt();
  }

  /* ───────────────────────────────────────────────────────────
   * ⑤ Reading speed + comprehension
   * ───────────────────────────────────────────────────────── */

  var READS = {
    B1: [{
      title: "Un nouveau quartier prend vie à Trois-Rivières",
      text: "Depuis l'an dernier, le quartier du Vieux-Port de Trois-Rivières connaît une transformation visible. Les anciens entrepôts ont été reconvertis en bureaux et en logements. Trois cafés indépendants ont ouvert leurs portes en moins de six mois, et un marché public hebdomadaire attire des centaines de familles chaque samedi. Les commerçants locaux saluent ce mouvement, mais s'inquiètent aussi des loyers commerciaux qui ont presque doublé depuis 2024. La municipalité affirme qu'elle veillera à préserver la diversité des commerces et à maintenir des programmes d'aide pour les petits artisans qui souhaitent rester dans le secteur. Plusieurs résidents de longue date espèrent que le caractère convivial du quartier ne disparaîtra pas sous la pression du développement immobilier. Le maire a annoncé une consultation publique pour le mois prochain afin de recueillir les avis des habitants sur l'avenir du Vieux-Port et sur les priorités de la prochaine phase de rénovation. La date exacte sera communiquée par voie de presse.",
      qs: [
        { q: "Quel changement le quartier connaît-il ?", options: ["Un déclin économique", "Une transformation urbaine", "Un dépeuplement", "Une démolition complète"], correct: 1 },
        { q: "Quelle inquiétude est mentionnée ?", options: ["Le manque de touristes", "La hausse des loyers commerciaux", "La pollution", "Le bruit nocturne"], correct: 1 },
        { q: "Que prévoit la municipalité ?", options: ["Une fermeture des commerces", "Une consultation publique", "Une augmentation des taxes", "Un nouveau pont"], correct: 1 }
      ]
    }],
    B2: [{
      title: "Faut-il rendre obligatoire l'apprentissage d'une seconde langue ?",
      text: "Le débat sur l'enseignement obligatoire d'une seconde langue au primaire ressurgit régulièrement. Ses partisans avancent que la précocité de l'exposition favorise non seulement la maîtrise linguistique, mais aussi la flexibilité cognitive et l'ouverture culturelle. Plusieurs études longitudinales semblent confirmer ces bénéfices, bien que leur ampleur reste discutée. Les détracteurs, eux, soulignent que la charge ajoutée au curriculum risque de fragiliser les apprentissages fondamentaux — lecture, calcul, écriture en langue première — chez les enfants qui peinent déjà à les consolider. Le débat n'oppose donc pas, à proprement parler, partisans et adversaires de l'enseignement des langues, mais deux conceptions de la priorité scolaire : celle d'une école qui mise sur l'élargissement précoce des compétences, et celle qui privilégie d'abord la consolidation des bases. Aucune des deux positions n'est moralement supérieure ; chacune répond à un diagnostic différent de ce dont les élèves ont besoin aujourd'hui. La décision politique, en définitive, dépendra de ce diagnostic-là.",
      qs: [
        { q: "L'auteur considère que le débat est…", options: ["Pour ou contre l'enseignement des langues", "Une opposition entre deux conceptions de la priorité scolaire", "Une question purement budgétaire", "Une bataille idéologique"], correct: 1 },
        { q: "Quelle est la position de l'auteur sur les deux camps ?", options: ["Il rejette les partisans", "Il rejette les détracteurs", "Il considère qu'aucune position n'est moralement supérieure", "Il refuse de prendre position politiquement"], correct: 2 },
        { q: "Selon l'auteur, la décision politique dépendra…", options: ["Du budget", "Du diagnostic posé sur les besoins des élèves", "De la pression syndicale", "Des résultats internationaux"], correct: 1 }
      ]
    }],
    C1: [{
      title: "L'illusion de la transparence numérique",
      text: "On voudrait nous faire croire que l'ère numérique a rendu nos vies plus transparentes. À en juger par la profusion de données que nous produisons quotidiennement, l'argument paraît imparable. Or, à y regarder de près, jamais l'opacité n'a été aussi grande. Les algorithmes qui hiérarchisent l'information sont, pour la plupart d'entre eux, des boîtes noires dont même leurs concepteurs peinent à expliquer les décisions. Ce que nous voyons à l'écran n'est plus une fenêtre sur le monde, mais le résultat d'un calcul fait pour nous — c'est-à-dire, le plus souvent, à notre place. Sous couvert de personnalisation, c'est un appauvrissement de l'horizon commun qui s'opère, lent, indolore, et largement inconscient. Loin de nous éclairer, cette technologie nous prive d'une condition fondamentale du jugement : celle de pouvoir comparer ce que nous voyons à ce que voient les autres. La transparence supposée n'est, en définitive, qu'une transparence inversée — celle qui nous expose, sans nous donner les moyens de comprendre par quel mécanisme nous sommes ainsi exposés.",
      qs: [
        { q: "La thèse principale de l'auteur est que…", options: ["L'ère numérique a rendu nos vies transparentes", "L'opacité est désormais plus grande qu'avant", "Les algorithmes améliorent le jugement", "La personnalisation est neutre"], correct: 1 },
        { q: "Que critique l'auteur dans la personnalisation algorithmique ?", options: ["Son coût financier", "L'appauvrissement de l'horizon commun", "La lenteur des serveurs", "L'absence de cadre légal"], correct: 1 },
        { q: "« Transparence inversée » signifie ici…", options: ["Une transparence accrue", "Une transparence qui nous expose sans nous éclairer", "Un effet d'optique", "Une métaphore commerciale"], correct: 1 }
      ]
    }]
  };

  var rState = { passage: null, started: 0, timer: null };

  function rPick() {
    var lvl = document.getElementById("read-level").value;
    var pool = READS[lvl];
    rState.passage = pool[Math.floor(Math.random() * pool.length)];
  }
  function rStart() {
    rPick();
    var p = rState.passage;
    var box = document.getElementById("read-passage");
    box.innerHTML = '<h4 class="read-title">' + p.title + '</h4><p class="read-body" lang="fr">' + p.text + '</p>' +
      '<button class="btn btn-primary" id="read-done">I have finished reading →</button>';
    document.getElementById("read-questions").hidden = true;
    document.getElementById("read-result").hidden = true;
    rState.started = Date.now();
    if (rState.timer) clearInterval(rState.timer);
    rState.timer = setInterval(function () {
      var s = Math.floor((Date.now() - rState.started) / 1000);
      var m = Math.floor(s / 60), r = s % 60;
      document.getElementById("read-time").textContent = (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r;
    }, 250);
    document.getElementById("read-done").addEventListener("click", rFinishReading);
  }
  function rFinishReading() {
    clearInterval(rState.timer); rState.timer = null;
    var seconds = Math.round((Date.now() - rState.started) / 1000);
    var words = rState.passage.text.split(/\s+/).length;
    var wpm = Math.round((words / Math.max(1, seconds)) * 60);
    rState.wpm = wpm;
    var qbox = document.getElementById("read-questions");
    var html = '<h4>Comprehension check (no looking back)</h4>';
    rState.passage.qs.forEach(function (q, i) {
      html += '<div class="read-q"><p class="read-q-text" lang="fr"><strong>' + (i + 1) + ".</strong> " + q.q + '</p>';
      html += '<div class="read-q-opts">';
      q.options.forEach(function (o, j) {
        html += '<label class="read-q-opt"><input type="radio" name="rq' + i + '" value="' + j + '"><span lang="fr">' + o + '</span></label>';
      });
      html += '</div></div>';
    });
    html += '<button class="btn btn-primary" id="read-grade">Grade me</button>';
    qbox.innerHTML = html;
    qbox.hidden = false;
    document.getElementById("read-passage").innerHTML = '<p class="demo-note">Passage hidden. WPM measured: <strong>' + wpm + '</strong></p>';
    document.getElementById("read-grade").addEventListener("click", rGrade);
  }
  function rGrade() {
    var passage = rState.passage;
    var ok = 0;
    passage.qs.forEach(function (q, i) {
      var sel = document.querySelector('input[name="rq' + i + '"]:checked');
      var v = sel ? parseInt(sel.value, 10) : -1;
      if (v === q.correct) ok++;
    });
    var wpm = rState.wpm || 0;
    var hist = lsGet("read-history", []);
    hist.push({ ts: Date.now(), wpm: wpm, ok: ok, total: passage.qs.length, level: document.getElementById("read-level").value });
    lsSet("read-history", hist.slice(-100));
    var diag = wpm >= 150 && ok >= 2 ? "On T4-pace" : wpm >= 120 ? "Below T4-pace, T3 OK" : "Need more reading volume";
    var rb = document.getElementById("read-result");
    rb.innerHTML = '<h4>Result</h4>' +
      '<p>WPM: <strong>' + wpm + '</strong> · Comprehension: <strong>' + ok + " / " + passage.qs.length + '</strong> · Verdict: <strong>' + diag + '</strong></p>' +
      '<p class="demo-note">CE T4 (B2–C2) requires ~150 WPM with 80%+ comprehension. CE T3 is comfortable at 130 WPM.</p>' +
      '<button class="btn btn-secondary" id="read-again">Another passage</button>';
    rb.hidden = false;
    document.getElementById("read-again").addEventListener("click", rStart);
    markPractice(2);
  }

  if (document.getElementById("read-start")) {
    document.getElementById("read-start").addEventListener("click", rStart);
    document.getElementById("read-skip").addEventListener("click", rStart);
  }

  /* ───────────────────────────────────────────────────────────
   * Stats panel
   * ───────────────────────────────────────────────────────── */

  function renderStats() {
    var diag = lsGet("diagnostic", null);
    var sum = document.querySelector('[data-stat="diag-summary"]');
    if (sum) {
      if (diag && diag.est) {
        sum.textContent = diag.est.CO.nclc + " / " + diag.est.CE.nclc + " / " + diag.est.EE.nclc + " / " + diag.est.EO.nclc;
      } else sum.textContent = "—";
    }
    var srs = srsLoad();
    var learned = Object.values(srs).filter(function (s) { return s.reps && s.reps >= 2; }).length;
    var le = document.querySelector('[data-stat="vocab-learned"]');
    if (le) le.textContent = learned;
    var dhist = lsGet("dict-history", []);
    var passed = dhist.filter(function (d) { return d.pct >= 80; }).length;
    var dr = document.querySelector('[data-stat="dict-ratio"]');
    if (dr) dr.textContent = passed + " / " + dhist.length;
    var wc = document.querySelector('[data-stat="write-count"]');
    if (wc) wc.textContent = lsGet("write-count", 0);
    var rhist = lsGet("read-history", []);
    var wpmEl = document.querySelector('[data-stat="read-wpm"]');
    if (wpmEl) {
      if (rhist.length) {
        var wpms = rhist.map(function (r) { return r.wpm; }).sort(function (a, b) { return a - b; });
        wpmEl.textContent = wpms[Math.floor(wpms.length / 2)] + " wpm";
      } else wpmEl.textContent = "—";
    }
    renderLeeches(srs);
  }

  function renderLeeches(srs) {
    var panel = document.getElementById("leech-panel");
    var list = document.getElementById("leech-list");
    if (!panel || !list) return;
    var leeches = [];
    Object.keys(srs).forEach(function (id) {
      var st = srs[id];
      if (!st || st.ease == null) return;
      if (st.ease < 1.5 && (st.reps == null || st.reps < 5)) {
        var card = ALL_DECK.find(function (c) { return c.id === id; });
        if (card) leeches.push({ card: card, ease: st.ease, lastQ: st.lastQ });
      }
    });
    leeches.sort(function (a, b) { return a.ease - b.ease; });
    leeches = leeches.slice(0, 12);
    if (!leeches.length) { panel.hidden = true; return; }
    panel.hidden = false;
    list.innerHTML = leeches.map(function (l) {
      return '<li class="leech-item">' +
        '<span class="leech-fr" lang="fr">' + l.card.fr + '</span>' +
        '<span class="leech-en" lang="en">' + l.card.en + '</span>' +
        '<span class="leech-ease">ease ' + l.ease.toFixed(2) + '</span>' +
        '</li>';
    }).join("");
  }

  // Export / reset
  var exp = document.getElementById("stats-export");
  if (exp) exp.addEventListener("click", function () {
    var out = {};
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf(LS_PREFIX) === 0) {
          out[k.substring(LS_PREFIX.length)] = JSON.parse(localStorage.getItem(k));
        }
      }
    } catch (e) {}
    var blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = "tcf-practice-stats-" + todayStr() + ".json";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });
  var rst = document.getElementById("stats-reset");
  if (rst) rst.addEventListener("click", function () {
    if (!confirm("Erase ALL local practice progress? This cannot be undone.")) return;
    try {
      var keys = [];
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf(LS_PREFIX) === 0) keys.push(k);
      }
      keys.forEach(function (k) { localStorage.removeItem(k); });
    } catch (e) {}
    location.reload();
  });

  /* ───────── Sparkline (last 30 days, minutes/day) ───────── */
  function renderSparkline() {
    var svg = document.getElementById("streak-spark");
    if (!svg) return;
    var hist = lsGet("history", {});
    var d = new Date(); d.setHours(0, 0, 0, 0);
    var pts = [];
    for (var i = 29; i >= 0; i--) {
      var k = new Date(d.getTime() - i * 86400000).toISOString().slice(0, 10);
      pts.push({ key: k, mins: hist[k] || 0 });
    }
    var max = Math.max.apply(null, pts.map(function (p) { return p.mins; }).concat([1]));
    // 30 bars across 300 viewBox width, 8px each + 2px gap = 10px.
    var html = "";
    pts.forEach(function (p, idx) {
      var h = Math.max(2, Math.round((p.mins / max) * 44));
      var x = idx * 10;
      var y = 48 - h;
      var cls = "streak-spark-bar" + (idx === pts.length - 1 ? " is-today" : "");
      html += '<rect class="' + cls + '" x="' + x + '" y="' + y + '" width="8" height="' + h + '" rx="1.5"><title>' + p.key + ' — ' + Math.round(p.mins) + ' min</title></rect>';
    });
    svg.innerHTML = html;
  }
  // Hook sparkline into the streak renderer so it stays in sync.
  var _origRenderStreak = renderStreak;
  renderStreak = function () { _origRenderStreak(); renderSparkline(); };

  /* ───────── Stats import (companion to export) ───────── */
  var imp = document.getElementById("stats-import");
  var impFile = document.getElementById("stats-import-file");
  if (imp && impFile) {
    imp.addEventListener("click", function () { impFile.click(); });
    impFile.addEventListener("change", function () {
      var f = impFile.files && impFile.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        try {
          var parsed = JSON.parse(e.target.result);
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("not an object");
          // Validate at least one known key — defensive, not exhaustive.
          var known = ["history", "sessions", "srs", "diagnostic", "dict-history", "read-history", "write-count"];
          var hits = known.filter(function (k) { return Object.prototype.hasOwnProperty.call(parsed, k); });
          if (!hits.length) throw new Error("no recognized keys");
          if (!confirm("Import will OVERWRITE your local progress with " + hits.length + " key(s) from this file. Continue?")) return;
          Object.keys(parsed).forEach(function (k) {
            try { localStorage.setItem(LS_PREFIX + k, JSON.stringify(parsed[k])); } catch (e2) {}
          });
          if (window.tcfToast) window.tcfToast("Imported. Reloading…");
          setTimeout(function () { location.reload(); }, 600);
        } catch (err) {
          alert("Could not parse import file: " + (err.message || err));
        }
      };
      reader.readAsText(f);
    });
  }

  renderStreak();
  renderStats();
})();
