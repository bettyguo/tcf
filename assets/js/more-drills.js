/* tcf-accel — More practice drills.
 *
 * Two more browser-only French training drills:
 *   ⑨ Speed-reading (RSVP) — rapid serial visual presentation of B1/B2/C1
 *      passages at a tunable WPM, followed by a 3-question comprehension
 *      check. Trains both reading rate AND chunk parsing.
 *   ⑩ Voice recorder for EO — uses MediaRecorder so learners can hear
 *      their own monologue back. Audio never leaves the browser.
 *
 * Both contribute to the streak / minutes tracker via the practice.js helper.
 */
(function () {
  "use strict";

  /* ───────── Shared helpers ───────── */

  var LS = "tcf.practice.";
  function lsGet(k, fb) {
    try { var v = localStorage.getItem(LS + k); return v == null ? fb : JSON.parse(v); }
    catch (e) { return fb; }
  }
  function lsSet(k, v) {
    try { localStorage.setItem(LS + k, JSON.stringify(v)); } catch (e) {}
  }
  function todayISO() { return new Date().toISOString().slice(0, 10); }
  function markPractice(minutes) {
    var hist = lsGet("history", {});
    var t = todayISO();
    hist[t] = (hist[t] || 0) + Math.max(0, minutes || 0);
    lsSet("history", hist);
    lsSet("sessions", lsGet("sessions", 0) + 1);
    if (typeof window.tcfRenderStreak === "function") window.tcfRenderStreak();
    if (typeof window.tcfCheckAchievements === "function") window.tcfCheckAchievements();
  }
  function escapeHTML(s) {
    return (s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" })[c];
    });
  }

  /* ═════════════════════════════════════════════════════════════
   * ⑨ Speed-reading (RSVP)
   * ═════════════════════════════════════════════════════════════ */

  // Passages indexed by CEFR level. Each comes with 3 MC questions.
  // Word counts target 90–130 words for a 30–60s read at typical WPM.
  var PASSAGES = [
    {
      level: "B1", id: "b1_residency",
      title: "Le centre d'accueil",
      fr: "Le centre d'accueil pour nouveaux arrivants propose chaque samedi matin des cours de français gratuits, ouverts à tous les résidents permanents. L'inscription se fait en ligne, au plus tard le jeudi soir. Les places sont limitées à vingt personnes par session, mais le centre ouvre une liste d'attente pour les candidats refusés. À la fin de chaque trimestre, les participants reçoivent une attestation de présence qu'ils peuvent joindre à leur dossier de citoyenneté. Le programme dure douze semaines au total, et un test de niveau est organisé en début de cursus pour orienter chaque apprenant vers le bon groupe.",
      qs: [
        { q: "Quand a lieu l'inscription au cours ?", o:["Le samedi matin","Au plus tard le jeudi soir","Le vendredi","Le lundi"], c:1 },
        { q: "Combien de places sont disponibles par session ?", o:["10","15","20","25"], c:2 },
        { q: "Que reçoivent les participants à la fin du trimestre ?", o:["Une carte de membre","Un certificat de niveau","Une attestation de présence","Un permis de travail"], c:2 }
      ]
    },
    {
      level: "B1", id: "b1_workpermit",
      title: "Le permis de travail",
      fr: "Mon permis de travail expire en juin prochain. J'ai déposé ma demande de renouvellement il y a déjà trois mois, mais le délai de traitement peut atteindre dix mois selon le pays d'origine. Heureusement, mon employeur a accepté de prolonger mon contrat à durée déterminée pour couvrir la période d'attente. J'ai dû fournir une preuve de fonds suffisants, un casier judiciaire vierge, et une attestation de mon employeur précisant mon poste et ma rémunération. L'agente m'a accusé réception du dossier la semaine dernière. Maintenant, il ne me reste plus qu'à patienter — et à éviter tout déplacement à l'étranger.",
      qs: [
        { q: "Quand le permis de travail expire-t-il ?", o:["En mars","En mai","En juin","En septembre"], c:2 },
        { q: "Qu'a fait l'employeur pour aider ?", o:["Il a payé les frais","Il a prolongé le CDD","Il a écrit au gouvernement","Il a embauché un avocat"], c:1 },
        { q: "Que doit éviter le locuteur pendant l'attente ?", o:["Les déplacements à l'étranger","Les vacances","Le changement de logement","Le sport"], c:0 }
      ]
    },
    {
      level: "B2", id: "b2_teletravail",
      title: "Le télétravail à l'épreuve",
      fr: "Le télétravail, présenté il y a cinq ans comme la solution à tous les maux de la vie de bureau, fait aujourd'hui l'objet d'un débat plus nuancé. Si les enquêtes confirment un gain de concentration pour les tâches isolées, elles révèlent aussi un appauvrissement progressif des liens informels entre collègues. Les jeunes embauchés, en particulier, peinent à construire un réseau professionnel sans rencontres en personne. De plus, la frontière entre vie privée et vie professionnelle se brouille, ce qui pèse sur le sommeil et l'humeur. Certains employeurs imposent donc un retour partiel au bureau, non par méfiance, mais par souci d'équilibre collectif.",
      qs: [
        { q: "Quel bénéfice les enquêtes confirment-elles ?", o:["Plus d'autonomie","Plus de revenus","Plus de concentration","Plus de promotions"], c:2 },
        { q: "Quel groupe a le plus de mal avec le télétravail ?", o:["Les cadres supérieurs","Les jeunes embauchés","Les indépendants","Les chercheurs"], c:1 },
        { q: "Pourquoi certains employeurs imposent-ils un retour au bureau ?", o:["Par méfiance des salariés","Pour l'équilibre collectif","Pour baisser les salaires","Pour louer plus de bureaux"], c:1 }
      ]
    },
    {
      level: "B2", id: "b2_francisation",
      title: "Le poids du français au Canada",
      fr: "L'apprentissage du français reste un atout déterminant pour qui souhaite s'établir durablement au Canada. Non seulement il ouvre l'accès à plusieurs provinces — au-delà du seul Québec — mais il pèse aussi sur la grille de pointage de l'Express Entry, où des bonus substantiels sont accordés aux candidats bilingues. À cela s'ajoute un facteur moins visible : l'intégration sociale. Les nouveaux arrivants qui parlent français nouent plus facilement des liens dans les communautés francophones de l'Ontario, du Nouveau-Brunswick ou de l'Alberta, où la demande de main-d'œuvre francophone dépasse souvent l'offre. Apprendre cette langue, c'est donc à la fois cocher une case administrative et bâtir un capital relationnel.",
      qs: [
        { q: "Quel programme bonifie les candidats bilingues ?", o:["Le Programme étudiant","La résidence temporaire","L'Express Entry","Le visa humanitaire"], c:2 },
        { q: "Quelles provinces sont citées comme accueillantes pour les francophones ?", o:["Ontario, Nouveau-Brunswick, Alberta","Ontario seulement","Quebec et Manitoba","Colombie-Britannique seule"], c:0 },
        { q: "Qu'est-ce que le français permet de construire, au-delà du papier ?", o:["Une carrière en politique","Un capital relationnel","Un héritage","Un commerce"], c:1 }
      ]
    },
    {
      level: "C1", id: "c1_immigration",
      title: "Réformes de l'immigration",
      fr: "Le récent durcissement des seuils d'admissibilité à la résidence permanente a suscité un débat dont les ressorts dépassent largement la sphère administrative. Au-delà de la question chiffrée — combien de candidats accueillir, selon quels critères — se profile une interrogation plus profonde sur le pacte social que l'immigration vient renouveler. D'aucuns y voient un signal de rigueur indispensable face à la pression sur le logement et les services publics. D'autres dénoncent un repli dommageable, susceptible de tarir un vivier de compétences dont l'économie canadienne ne saurait se passer. Force est de constater que ni les indicateurs économiques ni les sondages d'opinion ne tranchent clairement, ce qui laisse au politique la lourde charge d'arbitrer dans l'incertitude.",
      qs: [
        { q: "Qu'est-ce qui a été récemment durci ?", o:["Les frais de visa","Les seuils d'admissibilité","Les peines pénales","Les taxes douanières"], c:1 },
        { q: "Quelle préoccupation est invoquée par les partisans de la rigueur ?", o:["La sécurité nationale","La pression sur le logement","Les écoles privées","Le climat"], c:1 },
        { q: "Comment l'auteur qualifie-t-il la décision politique ?", o:["Aisée et tranchée","Strictement économique","À prendre dans l'incertitude","Sans conséquence"], c:2 }
      ]
    },
    {
      level: "C1", id: "c1_teletravail_c1",
      title: "L'illusion de la productivité",
      fr: "Il n'en demeure pas moins que la mesure du gain de productivité induit par le télétravail tient souvent davantage de l'incantation que de la démonstration. Sans doute les économistes s'accordent-ils sur l'existence d'effets de premier ordre — moins de transports, moins d'interruptions —, mais la prise en compte des effets de second ordre — érosion du capital social interne, attrition silencieuse des juniors, dilution du sens collectif — modifie sensiblement le bilan. À supposer même que la productivité individuelle soit accrue, encore faudrait-il qu'elle s'agrège à l'échelle de l'organisation, ce qui n'a rien d'évident. La littérature récente, plus prudente que les éloges initiaux, invite à manier ces chiffres avec circonspection.",
      qs: [
        { q: "Quel reproche l'auteur fait-il aux études initiales ?", o:["Elles sont anciennes","Elles relèvent plus de l'incantation","Elles sont biaisées politiquement","Elles ignorent les transports"], c:1 },
        { q: "Que désigne « l'attrition silencieuse des juniors » ?", o:["Une grève","Une démission progressive","Un licenciement collectif","Une promotion rapide"], c:1 },
        { q: "Comment la littérature récente est-elle qualifiée ?", o:["Plus optimiste","Plus prudente","Plus polémique","Plus chiffrée"], c:1 }
      ]
    }
  ];

  var rs = {
    passage: null,
    wpm: 280,
    chunk: 1,
    idx: 0,
    started: 0,
    finished: false,
    timer: null,
    score: 0,
    answered: 0
  };

  function rsCurrentLevel() {
    var el = document.getElementById("rs-level");
    return el ? el.value : "B1";
  }
  function rsCurrentWpm() {
    var el = document.getElementById("rs-wpm");
    return el ? parseInt(el.value, 10) : 280;
  }
  function rsCurrentChunk() {
    var el = document.getElementById("rs-chunk");
    return el ? parseInt(el.value, 10) : 1;
  }

  function rsPickPassage(level) {
    var pool = PASSAGES.filter(function (p) { return p.level === level; });
    return pool[Math.floor(Math.random() * pool.length)];
  }

  function rsStart() {
    var intro = document.getElementById("rs-intro");
    if (intro) intro.hidden = true;
    var lvl = rsCurrentLevel();
    rs.passage = rsPickPassage(lvl);
    rs.wpm = rsCurrentWpm();
    rs.chunk = rsCurrentChunk();
    rs.idx = 0;
    rs.finished = false;
    rs.started = Date.now();

    var stage = document.getElementById("rs-stage");
    if (!stage) return;
    var words = rs.passage.fr.split(/\s+/);
    var chunks = [];
    for (var i = 0; i < words.length; i += rs.chunk) {
      chunks.push(words.slice(i, i + rs.chunk).join(" "));
    }
    var totalSec = Math.round((words.length / rs.wpm) * 60);

    stage.innerHTML =
      '<div class="rsvp-display">' +
      '  <div class="rsvp-meta">' +
      '    <span class="rsvp-meta-pill">' + rs.passage.level + ' · ' + rs.passage.title + '</span>' +
      '    <span class="rsvp-meta-pill">' + words.length + ' words</span>' +
      '    <span class="rsvp-meta-pill">' + rs.wpm + ' WPM · ~' + totalSec + 's</span>' +
      '  </div>' +
      '  <div class="rsvp-word" id="rs-word" lang="fr">…</div>' +
      '  <div class="rsvp-progress"><span id="rs-progress-fg"></span></div>' +
      '  <div class="rsvp-controls">' +
      '    <button class="btn btn-secondary" type="button" id="rs-pause">Pause (space)</button>' +
      '    <button class="btn btn-ghost" type="button" id="rs-stop">Stop &amp; quiz</button>' +
      '  </div>' +
      '</div>';

    var wordEl = document.getElementById("rs-word");
    var pfg = document.getElementById("rs-progress-fg");
    var paused = false;
    var msPerChunk = (60000 / rs.wpm) * rs.chunk;

    function tick() {
      if (paused) return;
      if (rs.idx >= chunks.length) {
        clearInterval(rs.timer);
        rsFinish();
        return;
      }
      wordEl.textContent = chunks[rs.idx];
      pfg.style.width = ((rs.idx + 1) / chunks.length * 100) + "%";
      rs.idx++;
    }
    rs.timer = setInterval(tick, msPerChunk);
    tick();

    var pauseBtn = document.getElementById("rs-pause");
    var stopBtn = document.getElementById("rs-stop");
    function togglePause() {
      paused = !paused;
      pauseBtn.textContent = paused ? "Resume (space)" : "Pause (space)";
    }
    pauseBtn.addEventListener("click", togglePause);
    stopBtn.addEventListener("click", function () { clearInterval(rs.timer); rsFinish(); });

    function onKey(e) {
      if (e.key === " " || e.key === "Spacebar") { e.preventDefault(); togglePause(); }
      else if (e.key === "Escape") { clearInterval(rs.timer); rsFinish(); }
    }
    document.addEventListener("keydown", onKey);
    rs._cleanup = function () { document.removeEventListener("keydown", onKey); };
  }

  function rsFinish() {
    if (rs._cleanup) rs._cleanup();
    rs.finished = true;
    var elapsed = (Date.now() - rs.started) / 1000;
    var stage = document.getElementById("rs-stage");
    if (!stage) return;
    var qs = rs.passage.qs;
    rs.score = 0;
    rs.answered = 0;
    var qHtml = "";
    qs.forEach(function (q, qi) {
      qHtml +=
        '<div class="rsvp-q" data-qi="' + qi + '">' +
        '  <p class="rsvp-q-text" lang="fr">' + (qi + 1) + '. ' + escapeHTML(q.q) + '</p>' +
        '  <div class="rsvp-q-opts">' +
        q.o.map(function (o, oi) {
          return '<button class="rsvp-q-opt" data-qi="' + qi + '" data-oi="' + oi + '" type="button" lang="fr">' +
            '<span class="rsvp-q-letter">' + String.fromCharCode(65 + oi) + '</span>' +
            '<span>' + escapeHTML(o) + '</span></button>';
        }).join("") +
        '  </div>' +
        '</div>';
    });
    stage.innerHTML =
      '<div class="rsvp-result">' +
      '  <p class="rsvp-result-eyebrow">Comprehension check</p>' +
      '  <h4>' + escapeHTML(rs.passage.title) + ' · ' + rs.wpm + ' WPM · ' + Math.round(elapsed) + 's</h4>' +
      qHtml +
      '  <div class="rsvp-finish" id="rs-finish" hidden></div>' +
      '</div>';
    stage.querySelectorAll(".rsvp-q-opt").forEach(function (b) {
      b.addEventListener("click", function () {
        var qi = parseInt(b.dataset.qi, 10);
        var oi = parseInt(b.dataset.oi, 10);
        var q = qs[qi];
        var qWrap = stage.querySelector('.rsvp-q[data-qi="' + qi + '"]');
        if (qWrap.classList.contains("is-answered")) return;
        qWrap.classList.add("is-answered");
        qWrap.querySelectorAll(".rsvp-q-opt").forEach(function (b2) { b2.classList.add("is-locked"); });
        b.classList.add(oi === q.c ? "is-correct" : "is-wrong");
        var correct = qWrap.querySelector('.rsvp-q-opt[data-oi="' + q.c + '"]');
        if (correct) correct.classList.add("is-correct-reveal");
        if (oi === q.c) rs.score++;
        rs.answered++;
        if (rs.answered >= qs.length) rsFinalize(elapsed);
      });
    });
  }

  function rsFinalize(elapsed) {
    var f = document.getElementById("rs-finish");
    if (!f) return;
    var words = rs.passage.fr.split(/\s+/).length;
    var actualWpm = Math.round((words / elapsed) * 60);
    var ok = rs.score >= 2;
    var verdict = ok
      ? (actualWpm >= 150 ? "✅ On pace — T4 reading speed achievable" : "✅ Comprehension OK — push WPM up next round")
      : (actualWpm >= 150 ? "⚠ Speed without comprehension — slow down next round" : "⚠ Slow and low — pick a level lower next round");
    f.hidden = false;
    f.innerHTML =
      '<div class="rsvp-finish-card">' +
      '  <div class="rsvp-finish-num">' + rs.score + ' / ' + rs.passage.qs.length + '</div>' +
      '  <div class="rsvp-finish-meta">' +
      '    <span>Comprehension: <strong>' + Math.round(rs.score / rs.passage.qs.length * 100) + '%</strong></span>' +
      '    <span>WPM achieved: <strong>' + actualWpm + '</strong></span>' +
      '    <span>Target WPM: <strong>' + rs.wpm + '</strong></span>' +
      '  </div>' +
      '  <p class="rsvp-finish-verdict">' + verdict + '</p>' +
      '  <div class="rsvp-finish-actions">' +
      '    <button class="btn btn-primary" id="rs-again">Another passage →</button>' +
      '    <button class="btn btn-secondary" id="rs-up">+20 WPM next time</button>' +
      '    <button class="btn btn-ghost" id="rs-down">−20 WPM next time</button>' +
      '  </div>' +
      '</div>';
    markPractice(Math.max(1, Math.round(elapsed / 60)));
    document.getElementById("rs-again").addEventListener("click", rsStart);
    document.getElementById("rs-up").addEventListener("click", function () {
      var w = document.getElementById("rs-wpm");
      if (w) { w.value = Math.min(600, parseInt(w.value, 10) + 20); document.getElementById("rs-wpm-val").textContent = w.value; }
      rsStart();
    });
    document.getElementById("rs-down").addEventListener("click", function () {
      var w = document.getElementById("rs-wpm");
      if (w) { w.value = Math.max(100, parseInt(w.value, 10) - 20); document.getElementById("rs-wpm-val").textContent = w.value; }
      rsStart();
    });
  }

  function mountRSVP() {
    var stage = document.getElementById("rs-stage");
    if (!stage) return;
    var startBtn = document.getElementById("rs-start");
    if (startBtn) startBtn.addEventListener("click", rsStart);
    var w = document.getElementById("rs-wpm");
    var wv = document.getElementById("rs-wpm-val");
    if (w && wv) {
      wv.textContent = w.value;
      w.addEventListener("input", function () { wv.textContent = w.value; });
    }
  }

  /* ═════════════════════════════════════════════════════════════
   * ⑩ Voice recorder for EO self-evaluation
   * ═════════════════════════════════════════════════════════════ */

  // 3 EO prompts (T1 / T2 / T3 shape).
  var EO_PROMPTS = [
    { tier: "T1 (60s)", id:"t1_intro", q: "Présente-toi en soixante secondes : ton nom, ta ville, ce que tu aimes faire le week-end. Parle sans notes.", seconds: 60, rubric:["Two ideas developed", "No long pauses (>3s)", "B1+ vocabulary range"] },
    { tier: "T2 (90s)", id:"t2_describe", q: "En quatre-vingt-dix secondes, raconte un voyage marquant : le lieu, ce que tu as fait, ce que tu as ressenti. Articule au moins deux temps verbaux différents.", seconds: 90, rubric:["Past tenses correctly used","Coherent chronology","B2 connectors (puis, ensuite, finalement)"] },
    { tier: "T3 (120s)", id:"t3_argue", q: "En deux minutes, défends ou rejette : « Les villes devraient interdire les voitures en centre-ville ». Donne deux arguments structurés et un contre-argument.", seconds: 120, rubric:["Position clear","Two distinct arguments","Counter-argument acknowledged","B2/C1 connectors"] }
  ];

  var vr = {
    prompt: EO_PROMPTS[0],
    mediaRec: null,
    stream: null,
    chunks: [],
    audioUrl: null,
    started: 0,
    timer: null,
    secondsLeft: 60,
    state: "idle" // idle | recording | done
  };

  function vrFmt(s) {
    var m = Math.floor(s / 60); var ss = s % 60;
    return m + ":" + (ss < 10 ? "0" : "") + ss;
  }

  function vrSetPrompt(id) {
    var p = EO_PROMPTS.find(function (pp) { return pp.id === id; }) || EO_PROMPTS[0];
    vr.prompt = p;
    vr.secondsLeft = p.seconds;
  }

  function vrRender() {
    var stage = document.getElementById("vr-stage");
    if (!stage) return;
    var p = vr.prompt;
    stage.innerHTML =
      '<div class="voicerec">' +
      '  <p class="voicerec-tier">' + p.tier + '</p>' +
      '  <p class="voicerec-q" lang="fr">' + escapeHTML(p.q) + '</p>' +
      '  <div class="voicerec-timer-row">' +
      '    <div class="voicerec-timer" id="vr-timer">' + vrFmt(vr.secondsLeft) + '</div>' +
      '    <div class="voicerec-status" id="vr-status">Ready</div>' +
      '  </div>' +
      '  <div class="voicerec-vu" id="vr-vu" aria-hidden="true">' +
      '    <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>' +
      '  </div>' +
      '  <div class="voicerec-controls">' +
      '    <button class="btn btn-primary" id="vr-start" type="button">● Record</button>' +
      '    <button class="btn btn-secondary" id="vr-stop" type="button" disabled>■ Stop</button>' +
      '  </div>' +
      '  <div class="voicerec-playback" id="vr-playback" hidden></div>' +
      '  <div class="voicerec-rubric"><h5>Self-rate</h5>' +
      '    <ul>' + p.rubric.map(function (r) { return '<li><label><input type="checkbox" data-rubric> ' + escapeHTML(r) + '</label></li>'; }).join("") + '</ul>' +
      '  </div>' +
      '</div>';
    var startBtn = document.getElementById("vr-start");
    var stopBtn = document.getElementById("vr-stop");
    startBtn.addEventListener("click", vrStart);
    stopBtn.addEventListener("click", vrStop);
  }

  function vrTick() {
    vr.secondsLeft--;
    var t = document.getElementById("vr-timer");
    if (t) t.textContent = vrFmt(Math.max(0, vr.secondsLeft));
    if (vr.secondsLeft <= 0) {
      vrStop();
    }
  }

  function vrUpdateVU(value) {
    var bars = document.querySelectorAll("#vr-vu span");
    var n = Math.min(bars.length, Math.round(value * bars.length));
    bars.forEach(function (b, i) { b.classList.toggle("is-on", i < n); });
  }

  function vrStart() {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      if (window.tcfToast) window.tcfToast("This browser doesn't support audio recording");
      return;
    }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      vr.stream = stream;
      vr.chunks = [];
      // Use a widely supported MIME, fall back to default if unsupported.
      var mr;
      try { mr = new MediaRecorder(stream, { mimeType: "audio/webm" }); }
      catch (e) { mr = new MediaRecorder(stream); }
      vr.mediaRec = mr;
      mr.ondataavailable = function (e) { if (e.data && e.data.size > 0) vr.chunks.push(e.data); };
      mr.onstop = function () {
        var blob = new Blob(vr.chunks, { type: mr.mimeType || "audio/webm" });
        if (vr.audioUrl) URL.revokeObjectURL(vr.audioUrl);
        vr.audioUrl = URL.createObjectURL(blob);
        var pb = document.getElementById("vr-playback");
        if (pb) {
          pb.hidden = false;
          pb.innerHTML =
            '<p class="voicerec-pb-label">Listen back — audio stays in your browser, nothing is uploaded</p>' +
            '<audio controls src="' + vr.audioUrl + '"></audio>';
        }
        var statusEl = document.getElementById("vr-status");
        if (statusEl) statusEl.textContent = "Stopped · review your recording above";
        markPractice(Math.max(1, Math.round((vr.prompt.seconds - vr.secondsLeft) / 60)));
      };
      // VU meter from analyser.
      try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var src = ctx.createMediaStreamSource(stream);
        var an = ctx.createAnalyser(); an.fftSize = 256;
        src.connect(an);
        var data = new Uint8Array(an.frequencyBinCount);
        function loop() {
          if (vr.state !== "recording") return;
          an.getByteFrequencyData(data);
          var sum = 0; for (var i = 0; i < data.length; i++) sum += data[i];
          var avg = sum / data.length / 255;
          vrUpdateVU(avg);
          requestAnimationFrame(loop);
        }
        vr._audioCtx = ctx; vr._loop = loop;
        loop();
      } catch (e) { /* VU meter optional */ }
      mr.start();
      vr.state = "recording";
      vr.started = Date.now();
      vr.secondsLeft = vr.prompt.seconds;
      vr.timer = setInterval(vrTick, 1000);
      var startBtn = document.getElementById("vr-start");
      var stopBtn = document.getElementById("vr-stop");
      var statusEl = document.getElementById("vr-status");
      if (startBtn) startBtn.disabled = true;
      if (stopBtn) stopBtn.disabled = false;
      if (statusEl) statusEl.textContent = "● Recording…";
      if (vr._loop) vr._loop();
    }).catch(function () {
      if (window.tcfToast) window.tcfToast("Microphone access denied");
    });
  }

  function vrStop() {
    if (vr.timer) { clearInterval(vr.timer); vr.timer = null; }
    if (vr.mediaRec && vr.mediaRec.state !== "inactive") {
      try { vr.mediaRec.stop(); } catch (e) {}
    }
    if (vr.stream) {
      try { vr.stream.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {}
      vr.stream = null;
    }
    vr.state = "done";
    var startBtn = document.getElementById("vr-start");
    var stopBtn = document.getElementById("vr-stop");
    if (startBtn) { startBtn.disabled = false; startBtn.textContent = "● Record again"; }
    if (stopBtn) stopBtn.disabled = true;
    vrUpdateVU(0);
  }

  function mountVoiceRecorder() {
    var stage = document.getElementById("vr-stage");
    if (!stage) return;
    var sel = document.getElementById("vr-prompt");
    if (sel) {
      sel.addEventListener("change", function () {
        vrSetPrompt(sel.value);
        vrRender();
      });
    }
    var startGate = document.getElementById("vr-start-gate");
    if (startGate) startGate.addEventListener("click", function () {
      var intro = document.getElementById("vr-intro");
      if (intro) intro.hidden = true;
      vrSetPrompt(sel ? sel.value : "t1_intro");
      vrRender();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { mountRSVP(); mountVoiceRecorder(); });
  } else { mountRSVP(); mountVoiceRecorder(); }
})();
