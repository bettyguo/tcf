/* tcf-accel — Extra practice drills.
 *
 * Two new drills loaded on /practice/:
 *   ⑦ Sentence cloze — fill the missing word; covers connectors,
 *      subjunctive triggers, prepositions, and agreement gotchas.
 *   ⑧ Number listening — hear a French number, type the digits.
 *
 * Both share localStorage namespace tcf.practice.* so they roll up
 * into the streak / minutes tracker that practice.js already owns.
 * They piggy-back on the same TTS / streak helpers via window.tcfMarkPractice,
 * which practice.js exposes (or we shim a fallback below).
 */
(function () {
  "use strict";

  /* ───────────────────────────────────────────────────────────
   * Shared helpers (mirror practice.js conventions, scoped here)
   * ───────────────────────────────────────────────────────── */

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
    // Prefer the practice.js implementation if exposed; otherwise mirror it.
    if (typeof window.tcfMarkPractice === "function") { window.tcfMarkPractice(minutes); return; }
    var hist = lsGet("history", {});
    var t = todayISO();
    hist[t] = (hist[t] || 0) + Math.max(0, minutes || 0);
    lsSet("history", hist);
    lsSet("sessions", lsGet("sessions", 0) + 1);
    if (typeof window.tcfRenderStreak === "function") window.tcfRenderStreak();
  }
  function findFrenchVoice() {
    if (!("speechSynthesis" in window)) return null;
    var voices = window.speechSynthesis.getVoices();
    if (!voices.length) return null;
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
    try { window.speechSynthesis.cancel(); } catch (e) {}
    var u = new SpeechSynthesisUtterance(text);
    u.voice = voice; u.lang = voice.lang;
    u.rate = rate || 0.95; u.pitch = 1.0;
    u.onend = function () { onend && onend(null); };
    u.onerror = function (e) { onend && onend(e.error || "tts-error"); };
    window.speechSynthesis.speak(u);
  }
  function stripAccents(s) {
    return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "");
  }
  function norm(s) {
    return stripAccents((s || "").toLowerCase().trim()).replace(/[.,;:!?…«»"'()—–]/g, "").replace(/\s+/g, " ");
  }

  /* ═════════════════════════════════════════════════════════════
   * ⑦ Sentence Cloze
   * ═════════════════════════════════════════════════════════════ */

  // Each item: { fr_template: "Il faut que tu ___ à l'heure.", answer: "sois",
  //              accept: [other forms], en: translation, hint: short cue, why: explanation, tag: category }
  // The ___ marker is replaced with an <input>. Multiple "accept" tokens are
  // treated as equally correct (e.g. "à l'" vs "à"). Grading is accent-tolerant
  // but exact-spelling otherwise.
  var CLOZE = [
    // Connectors
    { fr: "___ que la mesure soit utile, son application reste difficile.", a: "Bien", accept: ["bien"], en: "Although the measure is useful, applying it remains difficult.", hint: "concession + subjonctif", why: "« Bien que » introduces a concession and triggers the subjunctive.", tag: "connector" },
    { fr: "Je viens te voir ___ que tu m'expliques le dossier.", a: "afin", accept: ["pour"], en: "I'm coming to see you so that you can explain the file.", hint: "purpose", why: "« afin que » / « pour que » express purpose + subjonctif.", tag: "connector" },
    { fr: "Il pleuvait, ___ nous avons annulé la sortie.", a: "donc", accept: ["alors"], en: "It was raining, so we cancelled the outing.", hint: "consequence", why: "« donc » or « alors » express consequence.", tag: "connector" },
    { fr: "Tu peux venir, ___ tu préviens à l'avance.", a: "pourvu", accept: ["si"], en: "You can come, provided you give advance notice.", hint: "condition + subj.", why: "« pourvu que » + subjunctive expresses a condition.", tag: "connector" },
    { fr: "Le projet avance ___ que prévu.", a: "plus", accept: ["moins"], en: "The project is moving forward faster/slower than expected.", hint: "comparison", why: "« plus que » / « moins que » express comparison.", tag: "connector" },
    { fr: "Elle continue de courir ___ avoir mal au genou.", a: "malgré", accept: ["en dépit d'"], en: "She keeps running despite her knee hurting.", hint: "concession + infin.", why: "« malgré » takes a noun or « le fait de + infinitive ».", tag: "connector" },
    { fr: "C'est un argument valable, ___ révèle un manque de données.", a: "cependant", accept: ["pourtant", "néanmoins", "toutefois"], en: "It's a valid argument; however, it reveals a lack of data.", hint: "opposition (multiple OK)", why: "Many register-appropriate connectors fit: cependant, pourtant, néanmoins, toutefois.", tag: "connector" },

    // Subjunctive triggers
    { fr: "Il faut que tu ___ à l'heure pour l'entretien.", a: "sois", accept: ["sois"], en: "You need to be on time for the interview.", hint: "subj. of être (tu)", why: "« il faut que » triggers the subjunctive: tu sois.", tag: "subjunctive" },
    { fr: "Je doute qu'il ___ raison sur ce point.", a: "ait", accept: ["ait"], en: "I doubt he's right on this point.", hint: "subj. of avoir (il)", why: "« douter que » triggers the subjunctive: il ait.", tag: "subjunctive" },
    { fr: "Bien que nous ___ fatigués, nous avons terminé.", a: "soyons", accept: ["soyons"], en: "Although we were tired, we finished.", hint: "subj. of être (nous)", why: "« bien que » + subjunctive: nous soyons.", tag: "subjunctive" },
    { fr: "Je cherche un appartement qui ___ proche du métro.", a: "soit", accept: ["soit"], en: "I'm looking for an apartment that's close to the subway.", hint: "subj. — uncertain reference", why: "Antecedent doesn't yet exist → subjunctive.", tag: "subjunctive" },
    { fr: "Je suis ravi que vous ___ pu venir.", a: "ayez", accept: ["ayez"], en: "I'm delighted you could come.", hint: "subj. of avoir (vous)", why: "Emotion + que → subjunctive: vous ayez.", tag: "subjunctive" },
    { fr: "Quoi qu'il ___, nous tiendrons le délai.", a: "arrive", accept: ["advienne"], en: "Whatever happens, we'll meet the deadline.", hint: "fixed phrase", why: "« quoi qu'il arrive / advienne » — subjunctive set phrase.", tag: "subjunctive" },
    { fr: "Pour que tu ___ ton objectif, il faut une routine quotidienne.", a: "atteignes", accept: ["atteignes"], en: "For you to reach your goal, you need a daily routine.", hint: "subj. of atteindre (tu)", why: "« pour que » triggers subjunctive: tu atteignes.", tag: "subjunctive" },

    // Prepositions
    { fr: "Il habite ___ Montréal depuis cinq ans.", a: "à", accept: ["à"], en: "He's been living in Montreal for five years.", hint: "city → ?", why: "Cities take « à » in French.", tag: "preposition" },
    { fr: "Elle est née ___ Canada.", a: "au", accept: ["au"], en: "She was born in Canada.", hint: "masc. country", why: "Masculine country → « au »: au Canada.", tag: "preposition" },
    { fr: "Mes parents viennent ___ Italie.", a: "d'", accept: ["de l'", "d'"], en: "My parents come from Italy.", hint: "fem. country (origin)", why: "Feminine country origin → « d' » before vowel: d'Italie.", tag: "preposition" },
    { fr: "Je rêve ___ visiter les Rocheuses.", a: "de", accept: ["de"], en: "I dream of visiting the Rockies.", hint: "verb + ? + inf.", why: "« rêver de + infinitive ».", tag: "preposition" },
    { fr: "Elle pense souvent ___ son grand-père.", a: "à", accept: ["à"], en: "She often thinks about her grandfather.", hint: "verb + ? + person", why: "« penser à quelqu'un » — penser à for people.", tag: "preposition" },
    { fr: "Le train part ___ Lyon à dix-huit heures.", a: "pour", accept: ["pour", "vers"], en: "The train leaves for Lyon at 6 p.m.", hint: "destination", why: "« partir pour » + destination. « vers » also acceptable (approximate).", tag: "preposition" },
    { fr: "Il s'intéresse beaucoup ___ politique canadienne.", a: "à la", accept: ["à la"], en: "He's very interested in Canadian politics.", hint: "interest + def. art.", why: "« s'intéresser à » + definite article: à la politique.", tag: "preposition" },

    // Agreement (gender / number / participle)
    { fr: "Les fleurs que j'ai ___ sont magnifiques.", a: "cueillies", accept: ["cueillies"], en: "The flowers I picked are magnificent.", hint: "passé composé + COD before verb (fem. pl.)", why: "Direct object « les fleurs » precedes the verb → agreement: cueillies.", tag: "agreement" },
    { fr: "La lettre est ___ par le directeur.", a: "signée", accept: ["signée"], en: "The letter is signed by the director.", hint: "passive, fem. sing.", why: "Passive voice — past participle agrees with subject « la lettre »: signée.", tag: "agreement" },
    { fr: "Ce sont les documents que vous m'avez ___.", a: "envoyés", accept: ["envoyés"], en: "These are the documents you sent me.", hint: "COD before verb, masc. pl.", why: "COD « les documents » precedes verb → masc. pl. agreement: envoyés.", tag: "agreement" },
    { fr: "Cette décision est ___ aux nouveaux arrivants.", a: "destinée", accept: ["destinée"], en: "This decision is aimed at newcomers.", hint: "adj. fem. sing.", why: "Adjective agrees with « décision » (fem. sing.): destinée.", tag: "agreement" },
    { fr: "Les candidats ___ devront passer un entretien complémentaire.", a: "retenus", accept: ["retenus"], en: "The selected candidates will have to take an additional interview.", hint: "past part. as adj., masc. pl.", why: "Past participle used adjectivally agrees with « candidats »: retenus.", tag: "agreement" },

    // Articles / partitives
    { fr: "Tu veux ___ café avant la réunion ?", a: "du", accept: ["du", "un"], en: "Want some coffee before the meeting?", hint: "partitive", why: "Uncountable beverage → partitive « du ». « un café » also OK (a cup).", tag: "article" },
    { fr: "Je n'ai pas ___ temps pour ce projet.", a: "de", accept: ["de"], en: "I don't have time for this project.", hint: "negation rule", why: "Negation collapses partitives to « de ».", tag: "article" },
    { fr: "Elle fait ___ photographie depuis l'âge de douze ans.", a: "de la", accept: ["de la"], en: "She's been doing photography since she was twelve.", hint: "partitive + fem.", why: "« faire de la » + fem. activity: de la photographie.", tag: "article" },

    // Pronouns
    { fr: "Mon frère et moi, nous ___ téléphonons chaque dimanche.", a: "nous", accept: ["nous"], en: "My brother and I, we call each other every Sunday.", hint: "reciprocal", why: "Reciprocal action → reflexive « nous ».", tag: "pronoun" },
    { fr: "Le rapport, je ___ remettrai demain matin.", a: "le", accept: ["le"], en: "The report — I'll hand it in tomorrow morning.", hint: "direct object (masc.)", why: "« le rapport » → masc. sing. direct object pronoun: le.", tag: "pronoun" },
    { fr: "Mes collègues, je ___ ai déjà parlé du sujet.", a: "leur", accept: ["leur"], en: "My colleagues — I've already talked to them about it.", hint: "indirect object plural", why: "« parler à quelqu'un » → indirect object plural: leur.", tag: "pronoun" },
    { fr: "Il y a des risques, mais nous ___ sommes conscients.", a: "en", accept: ["en"], en: "There are risks, but we're aware of them.", hint: "of-them", why: "« être conscient de » → « en » replaces « de quelque chose ».", tag: "pronoun" },
    { fr: "À Toronto, j'___ vais demain pour deux jours.", a: "y", accept: ["y"], en: "I'm going there for two days tomorrow.", hint: "place pronoun", why: "« y » replaces a location (here Toronto).", tag: "pronoun" },

    // Express Entry / civic
    { fr: "La demande doit être ___ en bonne et due forme avant la date butoir.", a: "déposée", accept: ["soumise", "déposée"], en: "The application must be filed in proper form before the deadline.", hint: "passive, fem.", why: "Either « déposée » or « soumise » — both fit and agree fem.", tag: "civic" },
    { fr: "Le délai de ___ peut atteindre dix mois selon le pays d'origine.", a: "traitement", accept: ["traitement"], en: "Processing time can reach ten months depending on country of origin.", hint: "noun — admin", why: "« délai de traitement » — admin set phrase.", tag: "civic" },
    { fr: "Toute infraction au code peut ___ un refus du dossier.", a: "entraîner", accept: ["entraîner", "provoquer"], en: "Any code violation can lead to a refusal of the file.", hint: "verb — cause", why: "« entraîner » or « provoquer » fit causal sense.", tag: "civic" },

    // C1-level idiomatic
    { fr: "Il n'en ___ pas moins que ce point reste à débattre.", a: "demeure", accept: ["demeure"], en: "It nevertheless remains the case that this point is still to be debated.", hint: "fixed idiom", why: "« Il n'en demeure pas moins que » — C1 set phrase.", tag: "idiom" },
    { fr: "Force est ___ constater que les délais s'allongent.", a: "de", accept: ["de"], en: "One must acknowledge that delays are growing.", hint: "fixed phrase", why: "« Force est de + infinitive » — formal set phrase.", tag: "idiom" },
    { fr: "À mesure ___ les négociations avancent, les positions se rapprochent.", a: "que", accept: ["que"], en: "As negotiations progress, positions draw closer.", hint: "progression", why: "« à mesure que » — progression connector.", tag: "idiom" }
  ];

  function escapeHTML(s) {
    return (s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" })[c];
    });
  }

  var cz = {
    item: null,
    queue: [],
    correct: 0,
    wrong: 0,
    streak: 0,
    startedAt: 0,
    started: false
  };

  function czBuildQueue(tag) {
    var pool = tag === "all" ? CLOZE.slice() : CLOZE.filter(function (c) { return c.tag === tag; });
    // Fisher–Yates shuffle.
    for (var i = pool.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = pool[i]; pool[i] = pool[j]; pool[j] = t;
    }
    return pool;
  }

  function czNext() {
    if (!cz.queue.length) cz.queue = czBuildQueue(czCurrentTag());
    cz.item = cz.queue.shift();
    czRender();
  }
  function czCurrentTag() {
    var s = document.getElementById("cz-tag");
    return s ? s.value : "all";
  }
  function czUpdateCounters() {
    var ce = document.getElementById("cz-correct"); if (ce) ce.textContent = cz.correct;
    var we = document.getElementById("cz-wrong"); if (we) we.textContent = cz.wrong;
    var se = document.getElementById("cz-streak"); if (se) se.textContent = cz.streak;
  }

  function czRender() {
    var stage = document.getElementById("cz-stage");
    if (!stage || !cz.item) return;
    var it = cz.item;
    var parts = it.fr.split("___");
    var pre = parts[0] || "";
    var post = parts[1] || "";
    var width = Math.max(8, ((it.a || "").length + 3) * 0.6) + "em";
    stage.innerHTML =
      '<p class="cloze-sentence" lang="fr">' +
      '  <span class="cloze-pre">' + escapeHTML(pre) + '</span>' +
      '  <input class="cloze-blank" id="cz-blank" type="text" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" lang="fr" style="width:' + width + '" aria-label="Fill in the blank" />' +
      '  <span class="cloze-post">' + escapeHTML(post) + '</span>' +
      '  <span class="cloze-hint">' + escapeHTML(it.hint || "") + '</span>' +
      '</p>' +
      '<p class="cloze-translation">' + escapeHTML(it.en) + '</p>' +
      '<div class="cloze-actions">' +
      '  <button class="btn btn-primary" type="button" id="cz-check">Check (Enter)</button>' +
      '  <button class="btn btn-secondary" type="button" id="cz-skip">Skip →</button>' +
      '  <button class="btn btn-ghost" type="button" id="cz-listen" aria-label="Listen to the sentence">▶ Listen</button>' +
      '</div>';
    var input = document.getElementById("cz-blank");
    input.focus();
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); czCheck(); }
    });
    document.getElementById("cz-check").addEventListener("click", czCheck);
    document.getElementById("cz-skip").addEventListener("click", function () {
      cz.streak = 0;
      czUpdateCounters();
      czNext();
    });
    document.getElementById("cz-listen").addEventListener("click", function () {
      // Read the sentence with the input value if any (so partial guess is heard);
      // otherwise read with the right answer to give a clear audio reference.
      var v = (input.value || "").trim();
      var full = pre + (v || it.a) + post;
      speak(full, 0.92);
    });
  }

  function czCheck() {
    var input = document.getElementById("cz-blank");
    if (!input || !cz.item) return;
    var raw = input.value || "";
    var user = norm(raw);
    var accept = (cz.item.accept || [cz.item.a]).map(norm);
    if (accept.indexOf(norm(cz.item.a)) < 0) accept.push(norm(cz.item.a));
    var correct = accept.indexOf(user) >= 0;
    input.classList.toggle("is-correct", correct);
    input.classList.toggle("is-wrong", !correct);
    input.disabled = true;
    document.getElementById("cz-check").disabled = true;
    if (correct) { cz.correct++; cz.streak++; }
    else { cz.wrong++; cz.streak = 0; }
    czUpdateCounters();
    var stage = document.getElementById("cz-stage");
    var why = document.createElement("p");
    why.className = "cloze-explain" + (correct ? "" : " is-wrong");
    why.innerHTML = (correct ? "✓ " : "✗ ") +
      "<strong>" + escapeHTML(cz.item.a) + "</strong> — " + escapeHTML(cz.item.why);
    stage.appendChild(why);
    var nextBtn = document.createElement("button");
    nextBtn.className = "btn btn-primary";
    nextBtn.style.marginTop = "14px";
    nextBtn.type = "button";
    nextBtn.textContent = "Next item →";
    stage.appendChild(nextBtn);
    nextBtn.focus();
    nextBtn.addEventListener("click", czNext);
    document.addEventListener("keydown", function onKey(e) {
      if (e.key === "Enter" || e.key === "ArrowRight") {
        e.preventDefault();
        document.removeEventListener("keydown", onKey);
        czNext();
      }
    });
  }

  function mountCloze() {
    var stage = document.getElementById("cz-stage");
    if (!stage) return;
    var startBtn = document.getElementById("cz-start");
    if (startBtn) startBtn.addEventListener("click", function () {
      cz.started = true;
      cz.startedAt = Date.now();
      var intro = document.getElementById("cz-intro");
      if (intro) intro.hidden = true;
      cz.queue = czBuildQueue(czCurrentTag());
      czUpdateCounters();
      czNext();
    });
    var tagSel = document.getElementById("cz-tag");
    if (tagSel) tagSel.addEventListener("change", function () {
      cz.queue = czBuildQueue(czCurrentTag());
      if (cz.started) czNext();
    });
    // Mark a session every 6 answered items.
    var lastCount = 0;
    setInterval(function () {
      if (!cz.started) return;
      var done = cz.correct + cz.wrong;
      if (done - lastCount >= 6) {
        lastCount = done;
        markPractice(2); // 2 min per 6 items is a sensible proxy.
      }
    }, 3000);
  }

  /* ═════════════════════════════════════════════════════════════
   * ⑧ Number Listening — hear French number, type digits
   * ═════════════════════════════════════════════════════════════ */

  // Convert an integer 0..999_999 to French (ortho rectifiée-aware: hyphens).
  function intToFr(n) {
    if (n === 0) return "zéro";
    if (n < 0) return "moins " + intToFr(-n);
    if (n >= 1000000) return "" + n; // out of range — fallback
    var parts = [];
    var millions = Math.floor(n / 1000000); n %= 1000000;
    var thousands = Math.floor(n / 1000); n %= 1000;
    if (millions) {
      parts.push((millions === 1 ? "un" : intToFrUnder1000(millions)) + " million" + (millions > 1 ? "s" : ""));
    }
    if (thousands) {
      parts.push((thousands === 1 ? "" : intToFrUnder1000(thousands) + " ") + "mille");
    }
    if (n) parts.push(intToFrUnder1000(n));
    return parts.join(" ").replace(/\s+/g, " ").trim();
  }
  function intToFrUnder1000(n) {
    var out = [];
    var hundreds = Math.floor(n / 100); n %= 100;
    if (hundreds) {
      if (hundreds === 1) out.push("cent");
      else out.push(numLow(hundreds) + " cent" + (n === 0 ? "s" : ""));
    }
    if (n) out.push(intToFrUnder100(n));
    return out.join(" ");
  }
  function intToFrUnder100(n) {
    if (n < 17) return ["zéro","un","deux","trois","quatre","cinq","six","sept","huit","neuf","dix","onze","douze","treize","quatorze","quinze","seize"][n];
    if (n < 20) return "dix-" + intToFrUnder100(n - 10);
    if (n < 70) {
      var tens = Math.floor(n / 10) * 10;
      var rem = n % 10;
      var base = ({ 20:"vingt", 30:"trente", 40:"quarante", 50:"cinquante", 60:"soixante" })[tens];
      if (rem === 0) return base;
      if (rem === 1) return base + " et un";
      return base + "-" + numLow(rem);
    }
    if (n < 80) {
      // 70..79: soixante-dix, soixante et onze, soixante-douze...
      if (n === 71) return "soixante et onze";
      return "soixante-" + intToFrUnder100(n - 60);
    }
    if (n === 80) return "quatre-vingts";
    if (n < 100) {
      if (n === 81) return "quatre-vingt-un";
      return "quatre-vingt-" + intToFrUnder100(n - 80);
    }
    return "" + n;
  }
  function numLow(n) {
    return ["","un","deux","trois","quatre","cinq","six","sept","huit","neuf"][n];
  }

  function intToTime(hh, mm) {
    // Return spoken French time, e.g. "dix-huit heures quarante-cinq"
    var h = (hh === 0) ? "zéro heure" : (hh === 1 ? "une heure" : intToFr(hh) + " heures");
    if (mm === 0) return h;
    if (mm === 15) return h + " et quart";
    if (mm === 30) return h + " et demie";
    if (mm === 45) return h + " moins le quart";
    return h + " " + intToFr(mm);
  }

  var nd = {
    target: null,
    targetText: "",
    correct: 0,
    wrong: 0,
    streak: 0,
    mode: "int", // int | time | money
    rangeMax: 99
  };

  function ndPickInt(max) {
    return Math.floor(Math.random() * (max + 1));
  }
  function ndPickTime() {
    return { hh: Math.floor(Math.random() * 24), mm: [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55][Math.floor(Math.random() * 12)] };
  }
  function ndPickMoney(max) {
    // Returns euros.cents
    var euros = Math.floor(Math.random() * (max + 1));
    var cents = [0, 25, 50, 75, 99][Math.floor(Math.random() * 5)];
    return { euros: euros, cents: cents };
  }

  function ndCurrentMax() {
    var el = document.getElementById("nd-range");
    return el ? parseInt(el.value, 10) : 99;
  }
  function ndCurrentMode() {
    var el = document.querySelector('input[name="nd-mode"]:checked');
    return el ? el.value : "int";
  }

  function ndPick() {
    var mode = ndCurrentMode();
    nd.mode = mode;
    nd.rangeMax = ndCurrentMax();
    if (mode === "time") {
      var t = ndPickTime();
      nd.target = { type: "time", hh: t.hh, mm: t.mm, str: (t.hh < 10 ? "0" : "") + t.hh + ":" + (t.mm < 10 ? "0" : "") + t.mm };
      nd.targetText = intToTime(t.hh, t.mm);
    } else if (mode === "money") {
      var m = ndPickMoney(nd.rangeMax);
      var str = m.euros + (m.cents ? "," + (m.cents < 10 ? "0" : "") + m.cents : ",00");
      nd.target = { type: "money", euros: m.euros, cents: m.cents, str: str };
      var cents = m.cents;
      var spoken;
      if (cents === 0) spoken = intToFr(m.euros) + " euros";
      else spoken = intToFr(m.euros) + " euros " + intToFr(cents);
      nd.targetText = spoken;
    } else {
      var v = ndPickInt(nd.rangeMax);
      nd.target = { type: "int", value: v, str: String(v) };
      nd.targetText = intToFr(v);
    }
  }

  function ndUpdateCounters() {
    var ce = document.getElementById("nd-correct"); if (ce) ce.textContent = nd.correct;
    var we = document.getElementById("nd-wrong"); if (we) we.textContent = nd.wrong;
    var se = document.getElementById("nd-streak"); if (se) se.textContent = nd.streak;
    var ra = document.getElementById("nd-range-active");
    if (ra) ra.textContent = "0–" + ndCurrentMax();
  }

  function ndRender() {
    var stage = document.getElementById("nd-stage");
    if (!stage) return;
    var ph =
      nd.mode === "time" ? "hh:mm" :
      nd.mode === "money" ? "ex. 12,50" :
      "Type the number";
    stage.innerHTML =
      '<div class="numdrill-question">' +
      '  <p class="numdrill-prompt-label">Listen, then type what you hear</p>' +
      '  <button class="numdrill-play" id="nd-play" type="button" aria-label="Play the number">' +
      '    <svg viewBox="0 0 24 24" fill="none"><polygon points="6 4 20 12 6 20 6 4" fill="currentColor"/></svg>' +
      '  </button>' +
      '  <div class="numdrill-input-row">' +
      '    <input class="numdrill-input" id="nd-input" type="text" inputmode="' + (nd.mode === "time" ? "text" : "decimal") + '" autocomplete="off" placeholder="' + ph + '" aria-label="Your answer" />' +
      '  </div>' +
      '  <p class="numdrill-reveal" id="nd-reveal">&nbsp;</p>' +
      '</div>';
    var input = document.getElementById("nd-input");
    var playBtn = document.getElementById("nd-play");
    function play() {
      playBtn.classList.add("is-playing");
      speak(nd.targetText, 0.92, function () { playBtn.classList.remove("is-playing"); });
    }
    playBtn.addEventListener("click", play);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); ndCheck(); }
      else if ((e.metaKey || e.ctrlKey) && e.key === " ") { e.preventDefault(); play(); }
    });
    setTimeout(function () { input.focus(); play(); }, 60);
  }

  function ndCheck() {
    var input = document.getElementById("nd-input");
    var reveal = document.getElementById("nd-reveal");
    if (!input || !nd.target) return;
    var raw = (input.value || "").trim();
    if (!raw) return;
    var expect = nd.target.str;
    var ok;
    if (nd.target.type === "time") {
      // Accept "1845", "18:45", "18h45", "18 45"
      var norm = raw.replace(/[hH:.\s]/g, "");
      if (/^\d{3,4}$/.test(norm)) {
        var h, m;
        if (norm.length === 3) { h = parseInt(norm.slice(0,1),10); m = parseInt(norm.slice(1),10); }
        else { h = parseInt(norm.slice(0,2),10); m = parseInt(norm.slice(2),10); }
        ok = (h === nd.target.hh && m === nd.target.mm);
      } else ok = false;
    } else if (nd.target.type === "money") {
      var x = raw.replace(/€\s*$/, "").replace(/\s/g,"").replace(".", ",");
      ok = (x === expect) || (parseFloat(x.replace(",",".")) === parseFloat(expect.replace(",",".")));
    } else {
      var n = raw.replace(/\s/g, "");
      ok = (n === expect) || (parseInt(n, 10) === nd.target.value);
    }
    input.classList.toggle("is-correct", ok);
    input.classList.toggle("is-wrong", !ok);
    input.disabled = true;
    reveal.innerHTML = (ok ? "✓ " : "✗ ") +
      "<strong>" + expect + "</strong>" +
      ' — <span class="nd-fr">« ' + nd.targetText + ' »</span>';
    if (ok) { nd.correct++; nd.streak++; }
    else { nd.wrong++; nd.streak = 0; }
    ndUpdateCounters();
    // Auto-advance after a moment.
    setTimeout(function () {
      ndPick();
      ndRender();
    }, ok ? 900 : 1700);
  }

  function mountNumDrill() {
    var stage = document.getElementById("nd-stage");
    if (!stage) return;
    var startBtn = document.getElementById("nd-start");
    if (startBtn) startBtn.addEventListener("click", function () {
      var intro = document.getElementById("nd-intro");
      if (intro) intro.hidden = true;
      ndUpdateCounters();
      ndPick();
      ndRender();
    });
    function syncModeChips() {
      document.querySelectorAll('.nd-mode-chips .chip').forEach(function (c) {
        var inp = c.querySelector('input[type="radio"]');
        c.classList.toggle("is-primary", !!(inp && inp.checked));
      });
    }
    syncModeChips();
    document.querySelectorAll('input[name="nd-mode"]').forEach(function (r) {
      r.addEventListener("change", function () {
        syncModeChips();
        ndUpdateCounters();
        ndPick();
        ndRender();
      });
    });
    var range = document.getElementById("nd-range");
    if (range) range.addEventListener("change", function () {
      ndUpdateCounters();
      ndPick();
      ndRender();
    });
    // Session tracking — every 8 attempts ≈ 3 min.
    var last = 0;
    setInterval(function () {
      var done = nd.correct + nd.wrong;
      if (done - last >= 8) { last = done; markPractice(3); }
    }, 4000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { mountCloze(); mountNumDrill(); });
  } else { mountCloze(); mountNumDrill(); }
})();
