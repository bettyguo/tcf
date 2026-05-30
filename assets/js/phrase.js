/* tcf-accel — "Phrase du jour"
 *
 * Date-seeded daily French sentence on the landing page. The same date hits
 * the same item across all visitors, so when learners share screenshots they
 * line up. Tap the speaker to play TTS, tap the translation to reveal it.
 *
 * Corpus = 60 hand-curated NCLC 5–9 sentences, tagged by skill focus.
 * All data ships inline; no fetch, no network.
 */
(function () {
  "use strict";

  var PHRASES = [
    { fr: "Si j'avais su que le bureau fermait à dix-sept heures, je serais arrivé plus tôt.", en: "If I had known the office closed at 5 p.m., I would have come earlier.", tag: "Conditionnel passé · regret", nclc: 7 },
    { fr: "Bien que la mesure soit utile, son application reste difficile sur le terrain.", en: "Although the measure is useful, applying it in the field remains difficult.", tag: "Subjonctif · concession", nclc: 8 },
    { fr: "Le délai de traitement peut atteindre douze mois selon le pays d'origine.", en: "Processing time can reach twelve months depending on the country of origin.", tag: "Express Entry · délai", nclc: 6 },
    { fr: "Il n'en demeure pas moins que cette réforme manque d'ambition budgétaire.", en: "Nevertheless, this reform lacks budget ambition.", tag: "Argumentation · C1", nclc: 9 },
    { fr: "Je m'inscris à un cours de francisation pour améliorer mon expression écrite.", en: "I'm registering for a Francization class to improve my written expression.", tag: "Quebec · school", nclc: 5 },
    { fr: "Pourriez-vous me dire à quelle heure le prochain train pour Trois-Rivières part ?", en: "Could you tell me what time the next train to Trois-Rivières leaves?", tag: "Politesse · CO", nclc: 6 },
    { fr: "Faute d'engagement budgétaire pluriannuel, la mesure restera lettre morte.", en: "Without a multi-year budget commitment, the measure will remain a dead letter.", tag: "Argumentation · cause", nclc: 9 },
    { fr: "Mon permis de travail expire le quinze juin et j'ai déposé une demande de renouvellement.", en: "My work permit expires on June 15 and I've filed for a renewal.", tag: "Work permit", nclc: 6 },
    { fr: "Le centre communautaire offre des ateliers gratuits aux nouveaux arrivants chaque samedi matin.", en: "The community centre offers free workshops to newcomers every Saturday morning.", tag: "Civic life", nclc: 5 },
    { fr: "Sans doute la cohorte d'admission de 2026 sera-t-elle plus restreinte que la précédente.", en: "The 2026 admission cohort will doubtless be more limited than the previous one.", tag: "Inversion · register", nclc: 9 },
    { fr: "Je tiens à vous remercier sincèrement de l'attention que vous avez portée à ma demande.", en: "I'd like to thank you sincerely for the attention you gave my request.", tag: "Lettre formelle", nclc: 7 },
    { fr: "Quoi qu'il en soit, nous trouverons une solution avant la fin de la semaine.", en: "Whatever happens, we'll find a solution before the end of the week.", tag: "Subjonctif · workplace", nclc: 7 },
    { fr: "Le télétravail occasionnel est toléré, mais ce n'est pas un droit acquis.", en: "Occasional remote work is tolerated, but it's not an established right.", tag: "Work culture", nclc: 7 },
    { fr: "À mesure que la concertation avance, les positions des deux camps se rapprochent.", en: "As the consultation progresses, the two camps' positions are drawing closer.", tag: "Connector · progression", nclc: 8 },
    { fr: "Veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées.", en: "Please accept, Madam, Sir, the expression of my distinguished greetings.", tag: "Closing · lettre", nclc: 6 },
    { fr: "Les compétences transférables comptent souvent autant que l'expérience canadienne.", en: "Transferable skills often matter as much as Canadian experience.", tag: "Job market", nclc: 7 },
    { fr: "Je n'aurais jamais imaginé que l'hiver puisse être aussi long et aussi blanc.", en: "I'd never have imagined winter could be so long and so white.", tag: "Conditionnel + subjonctif", nclc: 8 },
    { fr: "Vous devez vous présenter au guichet muni d'une pièce d'identité avec photo.", en: "You must come to the counter with photo ID in hand.", tag: "Admin · CE", nclc: 6 },
    { fr: "Plus on parle français au quotidien, plus on prend confiance à l'oral.", en: "The more you speak French daily, the more confident you get speaking.", tag: "Comparison · habit", nclc: 6 },
    { fr: "Le secteur de l'intelligence artificielle connaît un essor sans précédent à Montréal.", en: "The AI sector is booming unprecedentedly in Montreal.", tag: "Tech · Quebec", nclc: 8 },
    { fr: "Faites valoir votre expérience à l'international dans votre lettre de motivation.", en: "Highlight your international experience in your cover letter.", tag: "CV / cover letter", nclc: 7 },
    { fr: "Je m'attends à ce que la décision tombe d'ici la fin du mois prochain.", en: "I expect the decision will come down by the end of next month.", tag: "Subjonctif · expectation", nclc: 7 },
    { fr: "Aucune candidature ne sera examinée si le dossier n'est pas complet à la date butoir.", en: "No application will be reviewed if the file isn't complete by the deadline.", tag: "Conditional · admin", nclc: 7 },
    { fr: "Le bilinguisme officiel n'est pas seulement symbolique, c'est une politique opérationnelle.", en: "Official bilingualism isn't just symbolic — it's an operational policy.", tag: "Civic · register", nclc: 8 },
    { fr: "Avant de soumettre votre demande, vérifiez que tous les justificatifs sont à jour.", en: "Before submitting your application, check that all supporting documents are up to date.", tag: "Imperative · admin", nclc: 6 },
    { fr: "Elle a fait valoir ses droits devant le tribunal après plusieurs mois de procédure.", en: "She asserted her rights before the court after several months of proceedings.", tag: "Legal", nclc: 8 },
    { fr: "Tant que la convention collective n'est pas signée, les conditions restent inchangées.", en: "As long as the collective agreement isn't signed, conditions remain unchanged.", tag: "Workplace", nclc: 7 },
    { fr: "À l'issue de la réunion, nous rédigerons un compte rendu détaillé.", en: "At the end of the meeting, we'll draft a detailed report.", tag: "Workplace · futur", nclc: 6 },
    { fr: "Il aurait fallu que tu me préviennes avant de prendre cette décision.", en: "You should have warned me before making this decision.", tag: "Subjonctif passé · reproach", nclc: 8 },
    { fr: "Le projet est mené à bien grâce à la coordination étroite des trois équipes.", en: "The project is brought to a successful close thanks to the close coordination of the three teams.", tag: "Workplace · result", nclc: 7 },
    { fr: "Mieux vaut prévenir que guérir — surtout face à un délai aussi serré.", en: "Better safe than sorry — especially with such a tight deadline.", tag: "Proverbe · workplace", nclc: 6 },
    { fr: "Tu n'es pas obligé d'accepter l'avenant, mais tu dois répondre par écrit.", en: "You're not required to accept the contract amendment, but you must respond in writing.", tag: "Workplace · rights", nclc: 7 },
    { fr: "Je vous saurais gré de bien vouloir me transmettre les pièces manquantes.", en: "I would be grateful if you would send me the missing documents.", tag: "Conditionnel · formal", nclc: 8 },
    { fr: "Quand bien même les négociations se prolongeraient, la grève serait évitable.", en: "Even if negotiations were to drag on, the strike would be avoidable.", tag: "Hypothèse · C1", nclc: 9 },
    { fr: "Mon emploi du temps est chargé, mais je peux te recevoir mardi en fin de matinée.", en: "My schedule is busy, but I can see you Tuesday late morning.", tag: "Workplace · schedule", nclc: 6 },
    { fr: "Apprendre une langue, c'est avant tout apprendre à habiter une autre manière de penser.", en: "Learning a language is above all learning to inhabit another way of thinking.", tag: "Reflection", nclc: 9 },
    { fr: "Le seuil d'admissibilité a été relevé, ce qui exclut désormais plusieurs profils.", en: "The eligibility threshold has been raised, which now excludes several profiles.", tag: "Express Entry · update", nclc: 8 },
    { fr: "Vous trouverez ci-joint le formulaire dûment rempli ainsi que les pièces justificatives.", en: "Please find attached the duly completed form along with the supporting documents.", tag: "Lettre formelle", nclc: 7 },
    { fr: "Je viens de me rendre compte qu'il manque une signature sur la deuxième page.", en: "I just realized that there's a signature missing on the second page.", tag: "Passé récent · admin", nclc: 6 },
    { fr: "Pour peu que l'on s'y mette tôt, l'objectif des douze semaines est atteignable.", en: "Provided you get started early, the twelve-week goal is achievable.", tag: "Subjonctif · condition", nclc: 9 },
    { fr: "L'intégration ne se décrète pas, elle se vit au quotidien avec ses voisins.", en: "Integration isn't decreed — it's lived daily with one's neighbours.", tag: "Civic · reflection", nclc: 8 },
    { fr: "Si tant est que cette interprétation soit juste, les conséquences seraient lourdes.", en: "If indeed this interpretation is correct, the consequences would be heavy.", tag: "Subjonctif · doubt", nclc: 9 },
    { fr: "Je n'ai pas pu assister à la réunion, j'étais en arrêt maladie depuis lundi.", en: "I couldn't attend the meeting — I've been on sick leave since Monday.", tag: "Workplace · health", nclc: 6 },
    { fr: "Vous êtes prié de bien vouloir respecter les horaires d'ouverture du service.", en: "You are kindly asked to respect the office hours of the service.", tag: "Passive · admin", nclc: 7 },
    { fr: "Au fur et à mesure que l'on progresse, les automatismes finissent par s'installer.", en: "As you progress, automatic responses gradually settle in.", tag: "Progression · learning", nclc: 7 },
    { fr: "Le climat de travail s'est nettement amélioré depuis la nomination de la nouvelle directrice.", en: "The work climate has noticeably improved since the new director's appointment.", tag: "Workplace · change", nclc: 7 },
    { fr: "À supposer que tu décroches le poste, dans combien de temps pourrais-tu démarrer ?", en: "Assuming you land the job, how soon could you start?", tag: "Subjonctif · hypothesis", nclc: 8 },
    { fr: "Cela fait trois mois que je révise tous les soirs, et je commence enfin à voir des résultats.", en: "I've been studying every evening for three months, and I'm finally starting to see results.", tag: "Time expression", nclc: 6 },
    { fr: "Le télétravail isole certains profils plus qu'il ne libère ceux qui sont déjà autonomes.", en: "Remote work isolates certain profiles more than it liberates those already independent.", tag: "Opinion · nuance", nclc: 9 },
    { fr: "Je préfère que vous me communiquiez votre réponse par écrit plutôt que de vive voix.", en: "I prefer that you give me your answer in writing rather than verbally.", tag: "Subjonctif · preference", nclc: 7 },
    { fr: "Inutile de dire que la concurrence dans ce secteur est devenue impitoyable.", en: "Needless to say, the competition in this sector has become merciless.", tag: "Idiom · register", nclc: 8 },
    { fr: "On ne saurait trop insister sur l'importance d'une lettre de motivation personnalisée.", en: "One cannot stress enough the importance of a personalized cover letter.", tag: "Modal · advice", nclc: 9 },
    { fr: "Je m'efforce chaque jour de parler français avec mes collègues, même si je fais des fautes.", en: "I make an effort every day to speak French with my colleagues, even when I make mistakes.", tag: "Habit · perseverance", nclc: 6 },
    { fr: "Force est de constater que les délais administratifs s'allongent d'année en année.", en: "One must acknowledge that administrative delays grow longer year after year.", tag: "Argumentation · C1", nclc: 9 },
    { fr: "Le fait que vous ayez déjà travaillé au Canada constitue un atout indéniable.", en: "The fact that you've already worked in Canada is an undeniable asset.", tag: "Subjonctif · value", nclc: 8 },
    { fr: "Nous mettons tout en œuvre pour que votre installation se passe le mieux possible.", en: "We're doing everything possible to make your settling-in go as smoothly as possible.", tag: "Subjonctif · service", nclc: 7 },
    { fr: "Vous n'êtes pas sans savoir que la situation économique reste préoccupante.", en: "You're undoubtedly aware that the economic situation remains worrying.", tag: "Litotes · formal", nclc: 9 },
    { fr: "Je ne saurais trop te recommander de relire ta production avant de la soumettre.", en: "I cannot recommend strongly enough that you reread your work before submitting it.", tag: "Modal · advice", nclc: 8 },
    { fr: "À condition d'être préparé, l'examen oral n'a rien d'insurmontable.", en: "Provided you're prepared, the oral exam isn't insurmountable.", tag: "Condition · exam", nclc: 7 },
    { fr: "Les autorités frontalières exigent désormais une attestation de niveau de langue à jour.", en: "Border authorities now require an up-to-date language proficiency certificate.", tag: "Admin · immigration", nclc: 7 }
  ];

  function todayKey() { return new Date().toISOString().slice(0, 10); }
  function dayIndexForDate(d) {
    // Deterministic per-day index — uses days since 2026-01-01 (a TCF-accel anchor date).
    var anchor = Date.UTC(2026, 0, 1);
    var t = Date.UTC(d.getFullYear(), d.getMonth(), d.getDate());
    var days = Math.floor((t - anchor) / 86400000);
    var n = PHRASES.length;
    return ((days % n) + n) % n;
  }
  function indexForDate(d) { return dayIndexForDate(d); }

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

  function mount() {
    var host = document.getElementById("phrase-of-the-day");
    if (!host) return;

    var idx = indexForDate(new Date());
    var p = PHRASES[idx];
    var revealed = false;

    function dateLabel() {
      try {
        return new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
      } catch (e) { return todayKey(); }
    }

    host.innerHTML =
      '<article class="phrase-card" aria-label="Phrase du jour">' +
      '  <div class="phrase-head">' +
      '    <span class="phrase-eyebrow">Phrase du jour</span>' +
      '    <span class="phrase-date">' + dateLabel() + '</span>' +
      '  </div>' +
      '  <p class="phrase-fr" lang="fr">' + p.fr + '</p>' +
      '  <p class="phrase-en is-hidden" id="phrase-en">' + p.en + '</p>' +
      '  <span class="phrase-tag">' + p.tag + ' · NCLC ' + p.nclc + '</span>' +
      '  <div class="phrase-actions">' +
      '    <button class="phrase-btn is-primary" type="button" id="phrase-play" aria-label="Play sentence">' +
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 4 20 12 6 20 6 4" fill="currentColor"/></svg>' +
      '      Listen' +
      '    </button>' +
      '    <button class="phrase-btn" type="button" id="phrase-slow" aria-label="Play slower">' +
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>' +
      '      Slow' +
      '    </button>' +
      '    <button class="phrase-btn" type="button" id="phrase-reveal" aria-pressed="false" aria-controls="phrase-en">' +
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>' +
      '      Reveal translation' +
      '    </button>' +
      '    <button class="phrase-btn" type="button" id="phrase-copy" aria-label="Copy French sentence">' +
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>' +
      '      Copy' +
      '    </button>' +
      '    <button class="phrase-btn" type="button" id="phrase-shuffle" aria-label="Pick a random sentence">' +
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>' +
      '      Surprise me' +
      '    </button>' +
      '  </div>' +
      '</article>';

    var fr = host.querySelector(".phrase-fr");
    var en = host.querySelector(".phrase-en");
    var playBtn = host.querySelector("#phrase-play");
    var slowBtn = host.querySelector("#phrase-slow");
    var revealBtn = host.querySelector("#phrase-reveal");
    var copyBtn = host.querySelector("#phrase-copy");
    var shuffleBtn = host.querySelector("#phrase-shuffle");
    var tag = host.querySelector(".phrase-tag");

    function updateContent(item) {
      p = item;
      fr.textContent = item.fr;
      en.textContent = item.en;
      tag.textContent = item.tag + " · NCLC " + item.nclc;
      revealed = false;
      en.classList.add("is-hidden");
      revealBtn.setAttribute("aria-pressed", "false");
      revealBtn.lastChild.textContent = " Reveal translation";
    }

    function speak(rate) {
      if (!("speechSynthesis" in window)) {
        if (window.tcfToast) window.tcfToast("This browser doesn't support speech synthesis");
        return;
      }
      var voice = findFrenchVoice();
      if (!voice) {
        if (window.tcfToast) window.tcfToast("No French voice installed on this device");
        return;
      }
      var btn = rate && rate < 1 ? slowBtn : playBtn;
      try { window.speechSynthesis.cancel(); } catch (e) {}
      var u = new SpeechSynthesisUtterance(p.fr);
      u.voice = voice; u.lang = voice.lang;
      u.rate = rate || 1.0; u.pitch = 1.0;
      btn.classList.add("is-playing");
      u.onend = function () { btn.classList.remove("is-playing"); };
      u.onerror = function () { btn.classList.remove("is-playing"); };
      window.speechSynthesis.speak(u);
    }

    playBtn.addEventListener("click", function () { speak(1.0); });
    slowBtn.addEventListener("click", function () { speak(0.72); });
    revealBtn.addEventListener("click", function () {
      revealed = !revealed;
      en.classList.toggle("is-hidden", !revealed);
      revealBtn.setAttribute("aria-pressed", revealed ? "true" : "false");
      revealBtn.lastChild.textContent = revealed ? " Hide translation" : " Reveal translation";
    });
    en.addEventListener("click", function () {
      if (en.classList.contains("is-hidden")) revealBtn.click();
    });
    copyBtn.addEventListener("click", function () {
      try {
        navigator.clipboard.writeText(p.fr).then(function () {
          if (window.tcfToast) window.tcfToast("Copied to clipboard");
        });
      } catch (e) { window.prompt("Copy the French sentence:", p.fr); }
    });
    shuffleBtn.addEventListener("click", function () {
      var nIdx;
      do { nIdx = Math.floor(Math.random() * PHRASES.length); }
      while (PHRASES[nIdx].fr === p.fr && PHRASES.length > 1);
      updateContent(PHRASES[nIdx]);
    });

    // Refresh the French voice list once the browser loads voices async.
    if ("speechSynthesis" in window && !findFrenchVoice()) {
      window.speechSynthesis.onvoiceschanged = function () {
        if (!findFrenchVoice()) {
          playBtn.disabled = true; slowBtn.disabled = true;
          playBtn.title = slowBtn.title = "No French voice installed on this device";
        }
      };
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
