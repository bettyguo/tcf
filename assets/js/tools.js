/*
 * tcf-accel — Tools page.
 * Five browser-only French mechanics utilities:
 *   ① Verb conjugator (32 verbs × 7 tenses, hand-curated paradigms)
 *   ② Number-to-French (0 – 1 000 000) with breath-group hints
 *   ③ Date / time builder (cardinal vs ordinal first; 24-hour clock)
 *   ④ Accent helper (clickable accented chars + scratchpad + copy)
 *   ⑤ IPA phoneme chart with French TTS samples
 *
 * No network, no logging. All paradigms are inline.
 */
(function () {
  "use strict";

  /* ───────── French TTS helper (lifted from practice.js shape) ───────── */
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
  function speak(text, rate) {
    if (!("speechSynthesis" in window)) return;
    var voice = findFrenchVoice();
    if (!voice) return;
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = rate || 0.95;
    u.pitch = 1.0;
    window.speechSynthesis.speak(u);
  }

  /* ────────────────────────────────────────────────────────────
   * ① Verb conjugator
   * ──────────────────────────────────────────────────────────── */

  // Each verb: { fr, en, ex, p:[je,tu,il,nous,vous,ils], pc:participle past, im:imparfait stem (1pl drop -ons),
  //              fs:[future stem], cd: same stem as future, sj:[je,tu,il,nous,vous,ils], ip:[tu,nous,vous],
  //              aux: "avoir" | "être" (for passé composé) }
  // imparfait endings: ais, ais, ait, ions, iez, aient.
  // conditionnel endings (on future stem): ais, ais, ait, ions, iez, aient.
  // futur simple endings (on future stem): ai, as, a, ons, ez, ont.
  // We render passé composé as aux.présent + participle (with être agreement marker noted but not declined).
  var VERBS = [
    { fr:"être", en:"to be", ex:"Je suis prêt à passer le test.",
      p:["suis","es","est","sommes","êtes","sont"], pc:"été", im:"ét", fs:"ser",
      sj:["sois","sois","soit","soyons","soyez","soient"], ip:["sois","soyons","soyez"], aux:"avoir" },
    { fr:"avoir", en:"to have", ex:"J'ai déposé ma demande hier.",
      p:["ai","as","a","avons","avez","ont"], pc:"eu", im:"av", fs:"aur",
      sj:["aie","aies","ait","ayons","ayez","aient"], ip:["aie","ayons","ayez"], aux:"avoir" },
    { fr:"aller", en:"to go", ex:"Je vais à Montréal en septembre.",
      p:["vais","vas","va","allons","allez","vont"], pc:"allé", im:"all", fs:"ir",
      sj:["aille","ailles","aille","allions","alliez","aillent"], ip:["va","allons","allez"], aux:"être" },
    { fr:"faire", en:"to do / make", ex:"Je fais mes devoirs après le travail.",
      p:["fais","fais","fait","faisons","faites","font"], pc:"fait", im:"fais", fs:"fer",
      sj:["fasse","fasses","fasse","fassions","fassiez","fassent"], ip:["fais","faisons","faites"], aux:"avoir" },
    { fr:"dire", en:"to say", ex:"Elle dit qu'elle viendra.",
      p:["dis","dis","dit","disons","dites","disent"], pc:"dit", im:"dis", fs:"dir",
      sj:["dise","dises","dise","disions","disiez","disent"], ip:["dis","disons","dites"], aux:"avoir" },
    { fr:"pouvoir", en:"can / to be able", ex:"Je peux venir lundi.",
      p:["peux","peux","peut","pouvons","pouvez","peuvent"], pc:"pu", im:"pouv", fs:"pourr",
      sj:["puisse","puisses","puisse","puissions","puissiez","puissent"], ip:[], aux:"avoir" },
    { fr:"vouloir", en:"to want", ex:"Je voudrais m'inscrire à ce cours.",
      p:["veux","veux","veut","voulons","voulez","veulent"], pc:"voulu", im:"voul", fs:"voudr",
      sj:["veuille","veuilles","veuille","voulions","vouliez","veuillent"], ip:["veuille","veuillons","veuillez"], aux:"avoir" },
    { fr:"devoir", en:"must / have to", ex:"Tu dois remettre le dossier vendredi.",
      p:["dois","dois","doit","devons","devez","doivent"], pc:"dû", im:"dev", fs:"devr",
      sj:["doive","doives","doive","devions","deviez","doivent"], ip:[], aux:"avoir" },
    { fr:"savoir", en:"to know (fact)", ex:"Je sais parler français.",
      p:["sais","sais","sait","savons","savez","savent"], pc:"su", im:"sav", fs:"saur",
      sj:["sache","saches","sache","sachions","sachiez","sachent"], ip:["sache","sachons","sachez"], aux:"avoir" },
    { fr:"voir", en:"to see", ex:"Nous voyons clairement le problème.",
      p:["vois","vois","voit","voyons","voyez","voient"], pc:"vu", im:"voy", fs:"verr",
      sj:["voie","voies","voie","voyions","voyiez","voient"], ip:["vois","voyons","voyez"], aux:"avoir" },
    { fr:"venir", en:"to come", ex:"Elle vient de finir.",
      p:["viens","viens","vient","venons","venez","viennent"], pc:"venu", im:"ven", fs:"viendr",
      sj:["vienne","viennes","vienne","venions","veniez","viennent"], ip:["viens","venons","venez"], aux:"être" },
    { fr:"prendre", en:"to take", ex:"Je prends le métro tous les jours.",
      p:["prends","prends","prend","prenons","prenez","prennent"], pc:"pris", im:"pren", fs:"prendr",
      sj:["prenne","prennes","prenne","prenions","preniez","prennent"], ip:["prends","prenons","prenez"], aux:"avoir" },
    { fr:"mettre", en:"to put / wear", ex:"Mets ton manteau, il fait froid.",
      p:["mets","mets","met","mettons","mettez","mettent"], pc:"mis", im:"mett", fs:"mettr",
      sj:["mette","mettes","mette","mettions","mettiez","mettent"], ip:["mets","mettons","mettez"], aux:"avoir" },
    { fr:"tenir", en:"to hold", ex:"Tiens ce dossier solidement.",
      p:["tiens","tiens","tient","tenons","tenez","tiennent"], pc:"tenu", im:"ten", fs:"tiendr",
      sj:["tienne","tiennes","tienne","tenions","teniez","tiennent"], ip:["tiens","tenons","tenez"], aux:"avoir" },
    { fr:"falloir", en:"to be necessary (3sg only)", ex:"Il faut absolument réviser.",
      p:["—","—","faut","—","—","—"], pc:"fallu", im:"fall", fs:"faudr",
      sj:["—","—","faille","—","—","—"], ip:[], aux:"avoir" },
    { fr:"croire", en:"to believe", ex:"Je crois qu'il a raison.",
      p:["crois","crois","croit","croyons","croyez","croient"], pc:"cru", im:"croy", fs:"croir",
      sj:["croie","croies","croie","croyions","croyiez","croient"], ip:["crois","croyons","croyez"], aux:"avoir" },
    { fr:"écrire", en:"to write", ex:"J'écris une lettre de motivation.",
      p:["écris","écris","écrit","écrivons","écrivez","écrivent"], pc:"écrit", im:"écriv", fs:"écrir",
      sj:["écrive","écrives","écrive","écrivions","écriviez","écrivent"], ip:["écris","écrivons","écrivez"], aux:"avoir" },
    { fr:"lire", en:"to read", ex:"Nous lisons la consigne attentivement.",
      p:["lis","lis","lit","lisons","lisez","lisent"], pc:"lu", im:"lis", fs:"lir",
      sj:["lise","lises","lise","lisions","lisiez","lisent"], ip:["lis","lisons","lisez"], aux:"avoir" },
    { fr:"connaître", en:"to know (person/place)", ex:"Je connais bien ce quartier.",
      p:["connais","connais","connaît","connaissons","connaissez","connaissent"], pc:"connu", im:"connaiss", fs:"connaîtr",
      sj:["connaisse","connaisses","connaisse","connaissions","connaissiez","connaissent"], ip:["connais","connaissons","connaissez"], aux:"avoir" },
    { fr:"vivre", en:"to live", ex:"Ils vivent à Québec depuis 2020.",
      p:["vis","vis","vit","vivons","vivez","vivent"], pc:"vécu", im:"viv", fs:"vivr",
      sj:["vive","vives","vive","vivions","viviez","vivent"], ip:["vis","vivons","vivez"], aux:"avoir" },
    { fr:"recevoir", en:"to receive", ex:"Vous recevrez la confirmation par courriel.",
      p:["reçois","reçois","reçoit","recevons","recevez","reçoivent"], pc:"reçu", im:"recev", fs:"recevr",
      sj:["reçoive","reçoives","reçoive","recevions","receviez","reçoivent"], ip:["reçois","recevons","recevez"], aux:"avoir" },
    { fr:"sortir", en:"to go out", ex:"Nous sortons ce soir.",
      p:["sors","sors","sort","sortons","sortez","sortent"], pc:"sorti", im:"sort", fs:"sortir",
      sj:["sorte","sortes","sorte","sortions","sortiez","sortent"], ip:["sors","sortons","sortez"], aux:"être" },
    { fr:"partir", en:"to leave", ex:"Le train part à 8 h 15.",
      p:["pars","pars","part","partons","partez","partent"], pc:"parti", im:"part", fs:"partir",
      sj:["parte","partes","parte","partions","partiez","partent"], ip:["pars","partons","partez"], aux:"être" },
    { fr:"dormir", en:"to sleep", ex:"Je dors mal cette semaine.",
      p:["dors","dors","dort","dormons","dormez","dorment"], pc:"dormi", im:"dorm", fs:"dormir",
      sj:["dorme","dormes","dorme","dormions","dormiez","dorment"], ip:["dors","dormons","dormez"], aux:"avoir" },
    { fr:"ouvrir", en:"to open", ex:"Elle ouvre la fenêtre.",
      p:["ouvre","ouvres","ouvre","ouvrons","ouvrez","ouvrent"], pc:"ouvert", im:"ouvr", fs:"ouvrir",
      sj:["ouvre","ouvres","ouvre","ouvrions","ouvriez","ouvrent"], ip:["ouvre","ouvrons","ouvrez"], aux:"avoir" },
    { fr:"offrir", en:"to offer", ex:"Le centre offre des cours gratuits.",
      p:["offre","offres","offre","offrons","offrez","offrent"], pc:"offert", im:"offr", fs:"offrir",
      sj:["offre","offres","offre","offrions","offriez","offrent"], ip:["offre","offrons","offrez"], aux:"avoir" },
    { fr:"finir", en:"to finish (-ir model)", ex:"Je finis le dossier ce soir.",
      p:["finis","finis","finit","finissons","finissez","finissent"], pc:"fini", im:"finiss", fs:"finir",
      sj:["finisse","finisses","finisse","finissions","finissiez","finissent"], ip:["finis","finissons","finissez"], aux:"avoir" },
    { fr:"parler", en:"to speak (-er model)", ex:"Je parle français couramment.",
      p:["parle","parles","parle","parlons","parlez","parlent"], pc:"parlé", im:"parl", fs:"parler",
      sj:["parle","parles","parle","parlions","parliez","parlent"], ip:["parle","parlons","parlez"], aux:"avoir" },
    { fr:"choisir", en:"to choose", ex:"Choisissez votre filière.",
      p:["choisis","choisis","choisit","choisissons","choisissez","choisissent"], pc:"choisi", im:"choisiss", fs:"choisir",
      sj:["choisisse","choisisses","choisisse","choisissions","choisissiez","choisissent"], ip:["choisis","choisissons","choisissez"], aux:"avoir" },
    { fr:"naître", en:"to be born", ex:"Elle est née à Montréal.",
      p:["nais","nais","naît","naissons","naissez","naissent"], pc:"né", im:"naiss", fs:"naîtr",
      sj:["naisse","naisses","naisse","naissions","naissiez","naissent"], ip:[], aux:"être" },
    { fr:"mourir", en:"to die", ex:"Mes grands-parents sont morts en 2018.",
      p:["meurs","meurs","meurt","mourons","mourez","meurent"], pc:"mort", im:"mour", fs:"mourr",
      sj:["meure","meures","meure","mourions","mouriez","meurent"], ip:["meurs","mourons","mourez"], aux:"être" },
    { fr:"rester", en:"to stay", ex:"Je suis resté chez moi.",
      p:["reste","restes","reste","restons","restez","restent"], pc:"resté", im:"rest", fs:"rester",
      sj:["reste","restes","reste","restions","restiez","restent"], ip:["reste","restons","restez"], aux:"être" }
  ];

  var PRONOUNS = ["je","tu","il/elle","nous","vous","ils/elles"];
  function elidedPronoun(verb, idx) {
    // je + vowel or silent h → j'
    if (idx !== 0) return PRONOUNS[idx];
    var first = (verb.p[0] || "").charAt(0).toLowerCase();
    if (["a","e","i","o","u","é","è","ê","â","î","ô","û","h"].indexOf(first) >= 0) return "j'";
    return "je";
  }

  function passeComposeRow(verb) {
    var aux = verb.aux === "être"
      ? ["suis","es","est","sommes","êtes","sont"]
      : ["ai","as","a","avons","avez","ont"];
    var ptcp = verb.pc;
    var rows = [];
    for (var i = 0; i < 6; i++) {
      var pron = i === 0
        ? (verb.aux === "être" ? "je " : "j'")
        : PRONOUNS[i] + " ";
      // For être verbs, mark agreement options (-e for f, -s for pl) as suffix tag.
      var agreementTag = "";
      if (verb.aux === "être" && !["—"].includes(ptcp)) {
        agreementTag = '<span class="conj-agree" title="Accord en genre/nombre avec le sujet">(·e/·s)</span>';
      }
      rows.push({
        pron: pron,
        form: aux[i] + " " + ptcp,
        agreement: agreementTag
      });
    }
    return rows;
  }

  function simpleRow(verb, forms) {
    // forms is an array of 6 conjugated forms (or "—").
    var rows = [];
    for (var i = 0; i < 6; i++) {
      var raw = forms[i] || "";
      var pron = i === 0 ? elidedPronoun({ p:[raw] }, 0) + (elidedPronoun({ p:[raw] }, 0) === "j'" ? "" : " ") : PRONOUNS[i] + " ";
      // If form is "—" (defective), don't elide.
      if (raw === "—") { pron = PRONOUNS[i] + " "; rows.push({ pron: pron, form: "—" }); continue; }
      rows.push({ pron: pron, form: raw });
    }
    return rows;
  }

  function imparfaitForms(verb) {
    if (verb.fr === "falloir") return ["—","—","fallait","—","—","—"];
    var stem = verb.im;
    return [
      stem + "ais", stem + "ais", stem + "ait",
      stem + "ions", stem + "iez", stem + "aient"
    ];
  }
  function futurForms(verb) {
    if (verb.fr === "falloir") return ["—","—","faudra","—","—","—"];
    var stem = verb.fs;
    return [stem + "ai", stem + "as", stem + "a", stem + "ons", stem + "ez", stem + "ont"];
  }
  function condForms(verb) {
    if (verb.fr === "falloir") return ["—","—","faudrait","—","—","—"];
    var stem = verb.fs;
    return [stem + "ais", stem + "ais", stem + "ait", stem + "ions", stem + "iez", stem + "aient"];
  }

  function imperativeRow(verb) {
    if (!verb.ip || verb.ip.length === 0) {
      return [{ pron:"", form:"<em class=\"muted\">(défectif — pas d'impératif)</em>" }];
    }
    return [
      { pron:"(tu) ", form: verb.ip[0] },
      { pron:"(nous) ", form: verb.ip[1] },
      { pron:"(vous) ", form: verb.ip[2] }
    ];
  }

  function subjonctifRow(verb) {
    var sj = verb.sj;
    var prelude = ["que je ","que tu ","qu'il/elle ","que nous ","que vous ","qu'ils/elles "];
    var rows = [];
    for (var i = 0; i < 6; i++) {
      if (sj[i] === "—") { rows.push({ pron: prelude[i].replace("que ", ""), form:"—" }); continue; }
      // Elide "que je" → "que j'" if subjunctive form starts with vowel.
      var pron = prelude[i];
      if (i === 0) {
        var first = (sj[i] || "").charAt(0).toLowerCase();
        if (["a","e","i","o","u","é","è","ê","â","î","ô","û","h"].indexOf(first) >= 0) pron = "que j'";
      }
      rows.push({ pron: pron, form: sj[i] });
    }
    return rows;
  }

  function renderConjugator() {
    var sel = document.getElementById("conj-verb");
    var verb = VERBS.find(function (v) { return v.fr === sel.value; });
    if (!verb) verb = VERBS[0];
    var tense = document.getElementById("conj-tense").value;

    var rows;
    var tenseLabel;
    if (tense === "présent") { rows = simpleRow(verb, verb.p); tenseLabel = "Présent de l'indicatif"; }
    else if (tense === "passé_composé") { rows = passeComposeRow(verb); tenseLabel = "Passé composé (auxiliaire " + verb.aux + ")"; }
    else if (tense === "imparfait") { rows = simpleRow(verb, imparfaitForms(verb)); tenseLabel = "Imparfait"; }
    else if (tense === "futur_simple") { rows = simpleRow(verb, futurForms(verb)); tenseLabel = "Futur simple"; }
    else if (tense === "conditionnel") { rows = simpleRow(verb, condForms(verb)); tenseLabel = "Conditionnel présent"; }
    else if (tense === "subjonctif") { rows = subjonctifRow(verb); tenseLabel = "Subjonctif présent"; }
    else if (tense === "impératif") { rows = imperativeRow(verb); tenseLabel = "Impératif présent"; }

    var html = '';
    html += '<div class="conj-head">';
    html += '  <div class="conj-head-l">';
    html += '    <h3>' + verb.fr + ' <span class="conj-en">— ' + verb.en + '</span></h3>';
    html += '    <p class="conj-tense-label">' + tenseLabel + '</p>';
    html += '  </div>';
    html += '  <button class="srs-tts conj-tts" type="button" aria-label="Hear paradigm">🔊 Hear paradigm</button>';
    html += '</div>';
    html += '<table class="conj-table">';
    html += '<thead><tr><th>Personne</th><th>Forme</th></tr></thead><tbody>';
    rows.forEach(function (r) {
      html += '<tr><td class="conj-pron">' + (r.pron || "") + '</td><td class="conj-form" lang="fr">' + r.form + (r.agreement || "") + '</td></tr>';
    });
    html += '</tbody></table>';
    html += '<div class="conj-ex" lang="fr"><span class="conj-ex-label">Exemple</span><p>' + verb.ex + '</p></div>';

    var out = document.getElementById("conj-readout");
    out.innerHTML = html;

    // Wire up TTS button.
    var tts = out.querySelector(".conj-tts");
    if (tts) {
      tts.addEventListener("click", function () {
        // Speak the form-only (no pronouns) so the listener can hear the paradigm.
        var phrase = rows.filter(function (r) { return r.form && r.form !== "—" && r.form.indexOf("<em") < 0; })
          .map(function (r) { return (r.pron || "") + r.form; }).join(". ");
        speak(phrase, 0.92);
      });
    }
  }

  function initConjugator() {
    var sel = document.getElementById("conj-verb");
    if (!sel) return;
    VERBS.forEach(function (v) {
      var o = document.createElement("option");
      o.value = v.fr; o.textContent = v.fr + " — " + v.en;
      sel.appendChild(o);
    });
    sel.value = "être";
    sel.addEventListener("change", renderConjugator);
    document.getElementById("conj-tense").addEventListener("change", renderConjugator);
    document.querySelectorAll('[data-jump-verb]').forEach(function (b) {
      b.addEventListener("click", function () { sel.value = b.dataset.jumpVerb; renderConjugator(); });
    });
    renderConjugator();
  }

  /* ────────────────────────────────────────────────────────────
   * ② Number → French
   * ──────────────────────────────────────────────────────────── */

  // 0–19, 20, 30, 40, 50, 60, 70, 80, 90 specials in standard French.
  var N_UNITS = ["zéro","un","deux","trois","quatre","cinq","six","sept","huit","neuf",
                 "dix","onze","douze","treize","quatorze","quinze","seize",
                 "dix-sept","dix-huit","dix-neuf"];
  var N_TENS = {20:"vingt",30:"trente",40:"quarante",50:"cinquante",60:"soixante",
                70:"soixante",80:"quatre-vingt",90:"quatre-vingt"}; // 70/90 use composite

  function under100(n) {
    if (n < 20) return N_UNITS[n];
    if (n === 71) return "soixante et onze";
    if (n === 81) return "quatre-vingt-un";
    if (n === 91) return "quatre-vingt-onze";
    if (n < 70) {
      var t = Math.floor(n / 10) * 10;
      var u = n % 10;
      if (u === 0) return N_TENS[t];
      if (u === 1 && [20,30,40,50,60].indexOf(t) >= 0) return N_TENS[t] + " et un";
      return N_TENS[t] + "-" + N_UNITS[u];
    }
    if (n < 80) { // 70..79 → soixante-dix..
      var rest = n - 60; // 10..19
      return "soixante-" + N_UNITS[rest];
    }
    // 80..99 → quatre-vingt(s) + …
    var rest2 = n - 80; // 0..19
    if (rest2 === 0) return "quatre-vingts"; // takes -s when alone
    return "quatre-vingt-" + N_UNITS[rest2];
  }

  function under1000(n) {
    if (n === 0) return "";
    if (n < 100) return under100(n);
    var h = Math.floor(n / 100);
    var rest = n % 100;
    var hWord = h === 1 ? "cent" : N_UNITS[h] + " cent";
    if (rest === 0) return h === 1 ? "cent" : N_UNITS[h] + " cents";
    return hWord + " " + under100(rest);
  }

  function numToFrench(n) {
    if (n === 0) return "zéro";
    if (n < 0) return "moins " + numToFrench(-n);
    if (n > 1000000) return "(au-dessus de 1 000 000)";
    var parts = [];
    var millions = Math.floor(n / 1000000);
    var rest = n % 1000000;
    if (millions === 1) parts.push("un million");
    else if (millions > 1) parts.push(under1000(millions) + " millions");
    var thousands = Math.floor(rest / 1000);
    rest = rest % 1000;
    if (thousands === 1) parts.push("mille");
    else if (thousands > 1) parts.push(under1000(thousands) + " mille");
    if (rest > 0) parts.push(under1000(rest));
    return parts.join(" ");
  }

  function numAlt(n) {
    // Belgian / Swiss equivalents for 70/80/90.
    if (n === 70) return "septante";
    if (n === 80) return "huitante (CH) / quatre-vingts (BE)";
    if (n === 90) return "nonante";
    return null;
  }

  function numHint(n) {
    if (n >= 100 && n < 200) return "Note: 100 = « cent » (sans « un »).";
    if (n >= 200 && (n % 100 === 0)) return "Note: « " + N_UNITS[Math.floor(n / 100)] + " cents » — le « s » tombe si un autre nombre suit.";
    if (n === 81 || n === 91) return "Pas de « et » : « quatre-vingt-un / -onze ».";
    if (n === 71) return "Note: « soixante et onze » (avec « et »).";
    if ((n % 100 === 80) && n !== 0) return "Pas de « s » à « quatre-vingt » quand suivi d'un autre nombre (sinon « quatre-vingts »).";
    if (n >= 1000 && n < 2000) return "Pour les dates < 2000 on dit aussi : « mil " + (n === 1000 ? "" : under1000(n - 1000)) + " » (variante historique).";
    return null;
  }

  function renderNumber() {
    var inp = document.getElementById("num-input");
    var raw = parseInt(inp.value, 10);
    if (isNaN(raw)) raw = 0;
    raw = Math.max(0, Math.min(1000000, raw));
    var fr = numToFrench(raw);
    var html = '';
    html += '<div class="num-out"><span class="num-out-label">' + raw.toLocaleString("fr-FR") + ' →</span><strong lang="fr">' + fr + '</strong>';
    html += '<button class="srs-tts num-tts" type="button" aria-label="Hear">🔊</button></div>';
    var alt = numAlt(raw);
    if (alt) html += '<p class="num-alt"><em>Variantes</em> : ' + alt + '</p>';
    var hint = numHint(raw);
    if (hint) html += '<p class="num-hint">' + hint + '</p>';
    // Currency form
    if (raw > 0) {
      html += '<p class="num-money"><em>Sous forme monétaire</em> : <span lang="fr">' + fr + ' dollars</span> · <span lang="fr">' + fr + ' euros</span></p>';
    }
    var out = document.getElementById("num-readout");
    out.innerHTML = html;
    out.querySelector(".num-tts").addEventListener("click", function () { speak(fr, 0.95); });
  }

  function initNumber() {
    var inp = document.getElementById("num-input");
    if (!inp) return;
    inp.addEventListener("input", renderNumber);
    document.querySelectorAll("[data-jump-num]").forEach(function (b) {
      b.addEventListener("click", function () { inp.value = b.dataset.jumpNum; renderNumber(); });
    });
    renderNumber();
  }

  /* ────────────────────────────────────────────────────────────
   * ③ Dates & time
   * ──────────────────────────────────────────────────────────── */

  var WEEKDAYS = ["dimanche","lundi","mardi","mercredi","jeudi","vendredi","samedi"];
  var MONTHS = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"];

  function dateInWords(iso) {
    if (!iso) return "";
    var d = new Date(iso + "T00:00:00");
    if (isNaN(d.getTime())) return "";
    var dow = WEEKDAYS[d.getDay()];
    var dayNum = d.getDate();
    var dayWord = dayNum === 1 ? "premier" : under100(dayNum);
    var month = MONTHS[d.getMonth()];
    var year = d.getFullYear();
    var yearWord = numToFrench(year);
    return "le " + dayWord + " " + month + " " + yearWord + " (" + dow + ")";
  }

  function timeInWords(hhmm) {
    if (!hhmm) return "";
    var parts = hhmm.split(":");
    var h = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10);
    if (isNaN(h) || isNaN(m)) return "";
    // 24-hour formal: "il est dix-huit heures quarante-cinq"
    var hWord = h === 0 ? "minuit" : h === 12 ? "midi" : under100(h) + " heures";
    var mWord;
    if (m === 0) mWord = h === 0 || h === 12 ? "" : "pile";
    else if (m === 15 && h !== 0 && h !== 12) mWord = "et quart";
    else if (m === 30 && h !== 0 && h !== 12) mWord = "et demie";
    else if (m === 45 && h !== 0 && h !== 12) {
      var nextH = (h + 1) % 24;
      hWord = (nextH === 12 ? "midi" : nextH === 0 ? "minuit" : under100(nextH) + " heures");
      mWord = "moins le quart";
    }
    else mWord = under100(m);
    var spoken = "il est " + hWord + (mWord ? " " + mWord : "");
    return spoken.trim();
  }

  function renderDateTime() {
    var d = document.getElementById("dt-date").value;
    var t = document.getElementById("dt-time").value;
    var html = '';
    if (d) {
      var dw = dateInWords(d);
      html += '<p class="dt-line"><span class="dt-label">Date écrite</span><strong lang="fr">' + dw + '</strong>';
      html += '<button class="srs-tts dt-tts" type="button" data-say="' + dw.replace(/"/g, "&quot;") + '" aria-label="Hear date">🔊</button></p>';
    }
    if (t) {
      var tw = timeInWords(t);
      html += '<p class="dt-line"><span class="dt-label">Heure parlée</span><strong lang="fr">' + tw + '</strong>';
      html += '<button class="srs-tts dt-tts" type="button" data-say="' + tw.replace(/"/g, "&quot;") + '" aria-label="Hear time">🔊</button></p>';
    }
    if (!html) html = '<p class="muted">Choose a date and/or time above.</p>';
    var out = document.getElementById("dt-readout");
    out.innerHTML = html;
    out.querySelectorAll(".dt-tts").forEach(function (b) {
      b.addEventListener("click", function () { speak(b.dataset.say, 0.95); });
    });
  }

  function initDateTime() {
    var d = document.getElementById("dt-date");
    var t = document.getElementById("dt-time");
    if (!d || !t) return;
    // Defaults: today + current time.
    var now = new Date();
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    d.value = now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
    t.value = pad(now.getHours()) + ":" + pad(now.getMinutes());
    d.addEventListener("change", renderDateTime);
    t.addEventListener("change", renderDateTime);
    renderDateTime();
  }

  /* ────────────────────────────────────────────────────────────
   * ④ Accent helper
   * ──────────────────────────────────────────────────────────── */

  function initAccents() {
    var pad = document.getElementById("acc-pad");
    var meta = document.getElementById("acc-meta");
    if (!pad) return;
    function refreshMeta() {
      if (!meta) return;
      meta.textContent = pad.value.length + " characters · " + (pad.value.match(/\S+/g) || []).length + " words";
    }
    document.querySelectorAll(".acc-key").forEach(function (b) {
      b.addEventListener("click", function () {
        var ch = b.dataset.ch;
        var start = pad.selectionStart || 0;
        var end = pad.selectionEnd || 0;
        var v = pad.value;
        pad.value = v.slice(0, start) + ch + v.slice(end);
        pad.selectionStart = pad.selectionEnd = start + ch.length;
        pad.focus();
        refreshMeta();
      });
    });
    pad.addEventListener("input", refreshMeta);
    document.getElementById("acc-copy").addEventListener("click", function () {
      try {
        navigator.clipboard.writeText(pad.value).then(function () {
          if (window.tcfToast) window.tcfToast("Copied " + pad.value.length + " characters");
        });
      } catch (e) {
        pad.select(); document.execCommand("copy");
      }
    });
    document.getElementById("acc-clear").addEventListener("click", function () {
      pad.value = ""; refreshMeta(); pad.focus();
    });
    refreshMeta();
  }

  /* ────────────────────────────────────────────────────────────
   * ⑤ IPA phoneme chart
   * ──────────────────────────────────────────────────────────── */

  var IPA = {
    vowels: [
      ["i", "ici", "lit"], ["e", "été", "blé"], ["ɛ", "père", "lait"],
      ["a", "patte", "plat"], ["ɑ", "pâte", "bas"], ["ɔ", "porte", "fort"],
      ["o", "rose", "beau"], ["u", "tout", "loup"], ["y", "tu", "sur"],
      ["ø", "feu", "bleu"], ["œ", "peur", "fleur"], ["ə", "le", "petit"]
    ],
    vowelsNasal: [
      ["ɛ̃", "vin", "pain"], ["ɑ̃", "blanc", "an"],
      ["ɔ̃", "bon", "son"], ["œ̃", "brun", "un"]
    ],
    semivowels: [
      ["j", "yeux", "fille"], ["w", "oui", "trois"], ["ɥ", "huit", "lui"]
    ],
    consonants: [
      ["p", "papa", "pain"], ["t", "tante", "thé"], ["k", "café", "qui"],
      ["b", "bébé", "bain"], ["d", "dans", "dé"], ["ɡ", "gare", "garçon"],
      ["f", "fer", "phare"], ["s", "ses", "cent"], ["ʃ", "chat", "schéma"],
      ["v", "voir", "wagon"], ["z", "zéro", "rose"], ["ʒ", "joue", "génie"],
      ["m", "main", "femme"], ["n", "nous", "année"], ["ɲ", "agneau", "Espagne"],
      ["l", "le", "elle"], ["ʁ", "rouge", "Paris"]
    ]
  };
  // For TTS, speak the example word (the IPA itself won't render correctly).
  function ipaTile(p) {
    return '<button class="ipa-tile" type="button" data-say="' + p[1] + '" title="' + p[2] + '">' +
      '<span class="ipa-sym">' + p[0] + '</span>' +
      '<span class="ipa-ex" lang="fr">' + p[1] + '</span>' +
      '</button>';
  }
  function initIPA() {
    var v = document.getElementById("ipa-vowels");
    var vn = document.getElementById("ipa-vowels-nasal");
    var s = document.getElementById("ipa-semivowels");
    var c = document.getElementById("ipa-consonants");
    if (!v) return;
    v.innerHTML = IPA.vowels.map(ipaTile).join("");
    vn.innerHTML = IPA.vowelsNasal.map(ipaTile).join("");
    s.innerHTML = IPA.semivowels.map(ipaTile).join("");
    c.innerHTML = IPA.consonants.map(ipaTile).join("");
    document.querySelectorAll(".ipa-tile").forEach(function (b) {
      b.addEventListener("click", function () { speak(b.dataset.say, 0.9); });
    });
  }

  /* ────────────────────────────────────────────────────────────
   * ⑥ Gender helper
   * ──────────────────────────────────────────────────────────── */

  // Override list for high-frequency exceptions. f=feminine, m=masculine.
  // Lowercased, accent-preserved keys.
  var GENDER_OVERRIDES = {
    // Looks feminine by suffix but masculine:
    "silence": "m", "génie": "m", "musée": "m", "lycée": "m", "trophée": "m",
    "athée": "m", "scarabée": "m", "pygmée": "m", "mausolée": "m",
    "rez-de-chaussée": "m",
    "incendie": "m", "génocide": "m", "remède": "m",
    // Looks masculine by suffix but feminine:
    "peau": "f", "eau": "f", "main": "f", "fin": "f", "faim": "f",
    "souris": "f", "perdrix": "f", "noix": "f", "voix": "f", "croix": "f",
    "image": "f", "page": "f", "cage": "f", "plage": "f", "rage": "f",
    "tige": "f", "horloge": "f", "loge": "f",
    "dent": "f", "jument": "f",
    // Common short words:
    "chose": "f", "fois": "f", "loi": "f", "foi": "f",
    "amour": "m", "honneur": "m", "bonheur": "m", "labeur": "m", "malheur": "m",
    "humeur": "f", "douleur": "f", "couleur": "f", "fleur": "f", "chaleur": "f", "peur": "f", "vapeur": "f", "rumeur": "f", "valeur": "f", "saveur": "f",
    // Greek-origin -e words (usually masculine):
    "problème": "m", "thème": "m", "système": "m", "schéma": "m", "diplôme": "m", "drame": "m", "programme": "m", "axe": "m", "code": "m", "mode": "m",
    "période": "f", "méthode": "f"
  };

  function guessGender(wordRaw) {
    var word = (wordRaw || "").toLowerCase().replace(/[.,;:!?«»"'()…—–]/g, "").trim();
    if (!word) return null;
    if (GENDER_OVERRIDES[word]) return { gender: GENDER_OVERRIDES[word], confidence: 0.98, rule: "override list" };
    // Strict suffix rules with rough confidence.
    var rules = [
      // feminine markers
      { suf: "tion",  g: "f", c: 0.97 }, { suf: "sion", g: "f", c: 0.95 },
      { suf: "ité",   g: "f", c: 0.97 }, { suf: "té",   g: "f", c: 0.85 },
      { suf: "ette",  g: "f", c: 0.96 },
      { suf: "ence",  g: "f", c: 0.90 }, { suf: "ance", g: "f", c: 0.92 },
      { suf: "ure",   g: "f", c: 0.85 },
      { suf: "esse",  g: "f", c: 0.93 },
      { suf: "ée",    g: "f", c: 0.80 },
      { suf: "ie",    g: "f", c: 0.78 },
      // masculine markers
      { suf: "age",   g: "m", c: 0.88 },
      { suf: "ment",  g: "m", c: 0.95 },
      { suf: "isme",  g: "m", c: 0.97 },
      { suf: "eau",   g: "m", c: 0.92 },
      { suf: "ier",   g: "m", c: 0.85 },
      { suf: "oir",   g: "m", c: 0.82 },
      { suf: "ail",   g: "m", c: 0.85 },
      { suf: "in",    g: "m", c: 0.78 },
      { suf: "on",    g: "m", c: 0.72 },
      { suf: "ateur", g: "m", c: 0.92 }
    ];
    for (var i = 0; i < rules.length; i++) {
      if (word.endsWith(rules[i].suf)) {
        return { gender: rules[i].g, confidence: rules[i].c, rule: "suffix « -" + rules[i].suf + " »" };
      }
    }
    // Fallback: unknown
    return { gender: "?", confidence: 0.0, rule: "no recognized suffix; check a dictionary" };
  }

  function renderGender() {
    var inp = document.getElementById("gen-input");
    var raw = (inp.value || "").trim();
    var out = document.getElementById("gen-readout");
    if (!raw) { out.innerHTML = '<p class="muted">Type a noun or short phrase above.</p>'; return; }
    var tokens = raw.split(/\s+/).filter(Boolean);
    var html = '<table class="gen-table"><thead><tr><th>Mot</th><th>Genre</th><th>Article</th><th>Confiance</th><th>Règle</th></tr></thead><tbody>';
    tokens.forEach(function (t) {
      var g = guessGender(t);
      if (!g) return;
      var label = g.gender === "f" ? "féminin" : g.gender === "m" ? "masculin" : "ambigu";
      var color = g.gender === "f" ? "gen-f" : g.gender === "m" ? "gen-m" : "gen-x";
      var article;
      var firstChar = (t.toLowerCase().replace(/[.,;:!?«»"'()…—–]/g, "")[0] || "");
      var isVowel = ["a","e","i","o","u","é","è","ê","â","î","ô","û","h"].indexOf(firstChar) >= 0;
      if (g.gender === "m") article = isVowel ? "l'" + t + " · un " + t : "le " + t + " · un " + t;
      else if (g.gender === "f") article = isVowel ? "l'" + t + " · une " + t : "la " + t + " · une " + t;
      else article = "—";
      var conf = Math.round(g.confidence * 100) + "%";
      html += '<tr><td lang="fr"><strong>' + t + '</strong></td><td class="' + color + '">' + label + '</td><td lang="fr">' + article + '</td><td>' + conf + '</td><td>' + g.rule + '</td></tr>';
    });
    html += '</tbody></table>';
    out.innerHTML = html;
  }
  function initGender() {
    var inp = document.getElementById("gen-input");
    if (!inp) return;
    inp.addEventListener("input", renderGender);
    document.querySelectorAll("[data-jump-gen]").forEach(function (b) {
      b.addEventListener("click", function () { inp.value = b.dataset.jumpGen; renderGender(); });
    });
    inp.value = "citoyenneté";
    renderGender();
  }

  /* ────────────────────────────────────────────────────────────
   * ⑦ Liaison preview
   * ──────────────────────────────────────────────────────────── */

  // h aspiré words — liaison FORBIDDEN. Compact list of high-frequency ones.
  var H_ASPIRE = new Set([
    "hibou","haricot","hauteur","haine","handicap","hameau","hangar","hanche",
    "harpe","hasard","hâte","hennir","hérisson","héros","hiérarchie",
    "hockey","honte","hors","huit","hurler","hutte","haut","huitième","houx",
    "hublot","hollande","homard","hibou","huitaine","huissier"
  ]);
  // Pronouns / determiners that trigger obligatoire liaison.
  var OBL_TRIGGER = new Set([
    "les","des","ces","mes","tes","ses","nos","vos","leurs",
    "un","deux","trois","six","dix",
    "nous","vous","ils","elles","on",
    "en","dans","sans","sous","chez",
    "quand","dont"
  ]);
  var ET_TRIGGER = "et"; // ALWAYS forbids liaison.

  function isVowelStart(w) {
    var ch = (w || "").toLowerCase().replace(/[.,;:!?«»"'()…—–]/g, "").charAt(0);
    return ["a","e","i","o","u","y","à","â","ä","é","è","ê","ë","î","ï","ô","ö","ù","û","ü"].indexOf(ch) >= 0
      || (ch === "h" && !H_ASPIRE.has((w || "").toLowerCase().replace(/[.,;:!?«»"'()…—–]/g, "")));
  }
  function endsConsForLiaison(w) {
    // Last char in the lower-cased, punctuation-stripped form. We care about silent s/x/z/t/d/n/p/r linkers.
    var cleaned = (w || "").toLowerCase().replace(/[.,;:!?«»"'()…—–]/g, "");
    var last = cleaned.charAt(cleaned.length - 1);
    return ["s","x","z","t","d","n","p","r","g"].indexOf(last) >= 0 ? last : null;
  }
  function linkSound(c) {
    return { s: "z", x: "z", z: "z", t: "t", d: "t", n: "n", p: "p", r: "ʁ", g: "k" }[c] || "?";
  }
  function liaisonKind(prevWord, nextWord) {
    var prev = (prevWord || "").toLowerCase().replace(/[.,;:!?«»"'()…—–]/g, "");
    var next = (nextWord || "").toLowerCase().replace(/[.,;:!?«»"'()…—–]/g, "");
    if (!prev || !next) return { kind: "none" };
    if (prev === ET_TRIGGER) return { kind: "interdite", reason: "après « et »" };
    if (next.charAt(0) === "h" && H_ASPIRE.has(next)) return { kind: "interdite", reason: "h aspiré" };
    if (!isVowelStart(nextWord)) return { kind: "none" };
    var c = endsConsForLiaison(prev);
    if (!c) return { kind: "none" };
    if (OBL_TRIGGER.has(prev)) return { kind: "obligatoire", sound: linkSound(c), reason: "déterminant / pronom obligatoire" };
    // Some adjectives before noun → obligatoire (petit, grand, bon, beau, vieux, mauvais)
    if (["petit","grand","bon","beau","vieux","mauvais","gros","long"].indexOf(prev) >= 0) {
      return { kind: "obligatoire", sound: linkSound(c), reason: "adjectif court + nom" };
    }
    // Otherwise facultative (verb + complement, prep + noun etc.)
    return { kind: "facultative", sound: linkSound(c), reason: "registre soutenu" };
  }

  function renderLiaison() {
    var inp = document.getElementById("liz-input");
    var raw = (inp.value || "").trim();
    var out = document.getElementById("liz-readout");
    if (!raw) { out.innerHTML = '<p class="muted">Tapez une phrase au-dessus.</p>'; return; }
    var tokens = raw.split(/(\s+)/); // keep whitespace tokens for output
    var words = raw.split(/\s+/).filter(Boolean);
    var html = '<p class="liz-out" lang="fr">';
    var w = 0;
    for (var i = 0; i < tokens.length; i++) {
      var tok = tokens[i];
      if (/^\s+$/.test(tok)) {
        // Decide liaison between prev word (words[w-1]) and next word (words[w]).
        if (w >= 1 && w < words.length) {
          var lk = liaisonKind(words[w - 1], words[w]);
          if (lk.kind === "obligatoire") {
            html += ' <span class="liaison-link liaison-ob" title="Obligatoire — ' + lk.reason + '"><span class="liaison-arc">‿</span><sub>/' + lk.sound + '/</sub></span> ';
          } else if (lk.kind === "facultative") {
            html += ' <span class="liaison-link liaison-fac" title="Facultative — ' + lk.reason + '"><span class="liaison-arc">‿</span><sub>/' + lk.sound + '/</sub></span> ';
          } else if (lk.kind === "interdite") {
            html += ' <span class="liaison-link liaison-int" title="Interdite — ' + lk.reason + '">⊘</span> ';
          } else {
            html += tok;
          }
        } else {
          html += tok;
        }
      } else {
        html += '<span class="liz-word">' + tok + '</span>';
        w++;
      }
    }
    html += '</p>';
    html += '<div class="liz-legend">' +
      '<span class="liaison-ob">obligatoire</span>' +
      '<span class="liaison-fac">facultative</span>' +
      '<span class="liaison-int">interdite</span></div>';
    out.innerHTML = html;
  }
  function initLiaison() {
    var inp = document.getElementById("liz-input");
    if (!inp) return;
    inp.addEventListener("input", renderLiaison);
    document.querySelectorAll("[data-jump-liz]").forEach(function (b) {
      b.addEventListener("click", function () { inp.value = b.dataset.jumpLiz; renderLiaison(); });
    });
    inp.value = "Les enfants vont en classe.";
    renderLiaison();
  }

  /* ───────── boot ───────── */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }
  function boot() {
    initConjugator();
    initNumber();
    initDateTime();
    initAccents();
    initIPA();
    initGender();
    initLiaison();
  }
})();
