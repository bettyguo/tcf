---
layout: default
title: "Tools"
eyebrow: "French mechanics toolkit"
subtitle: "Five quick browser-only utilities for the high-frequency French mechanics that trip up TCF Canada candidates: verb conjugation, numbers and dates, the accents row, and the IPA chart of French phonemes. Everything runs locally — no backend, no signup."
description: "French mechanics toolkit: verb conjugator (top 32 verbs · 7 tenses), number-to-French, date and time builder, accent helper, IPA phoneme chart with TTS."
scripts:
  - /assets/js/tools.js
  - /assets/js/converter.js
body_class: page-tools
---

<div class="callout callout-info">
  <p class="callout-title">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
    Mechanics, not training
  </p>
  <p>The <a href="{{ '/practice/' | relative_url }}">practice studio</a> trains the four TCF Canada skills. This page is its quieter sibling: the mechanics underneath. If a learner stalls on B1 verbs in the past tense, a writing prompt won't help — they need to <em>see</em> the conjugation. Same for big numbers in dictée (single-digit groups merge in connected speech), dates ("le quatorze juillet mille neuf cent quatre-vingt-neuf" parses three different ways), and accents (typing <code>e</code> vs. <code>é</code> shifts <em>diff-ok</em> to <em>diff-diacritic</em> in the dictée grader). Five focused tools, no scoring, no streak — just fast lookups.</p>
</div>

<nav class="learn-toc" aria-label="On this page">
  <a href="#conjugator">① Verb conjugator</a>
  <a href="#numbers">② Numbers</a>
  <a href="#dates">③ Dates &amp; time</a>
  <a href="#accents">④ Accent helper</a>
  <a href="#ipa">⑤ IPA phoneme chart</a>
  <a href="#gender">⑥ Gender helper</a>
  <a href="#liaison">⑦ Liaison preview</a>
  <a href="#converter">⑧ Score converter</a>
</nav>

## ① Verb conjugator — 32 essential verbs × 7 tenses {#conjugator}

> The B1 → B2 jump is largely a tense-mastery jump: the conditional and the subjunctive show up everywhere in argumentative writing (T3). Pick a verb, pick a tense, see the full paradigm and an example sentence at NCLC 6–8 register.

<section class="learn-card tool-card" data-tool="conj">
  <div class="conj-controls">
    <label for="conj-verb" class="nclc-control-label">Verb</label>
    <select id="conj-verb" class="select" aria-label="Verb"></select>
    <label for="conj-tense" class="nclc-control-label">Tense</label>
    <select id="conj-tense" class="select" aria-label="Tense">
      <option value="présent">Présent de l'indicatif</option>
      <option value="passé_composé">Passé composé</option>
      <option value="imparfait">Imparfait</option>
      <option value="futur_simple">Futur simple</option>
      <option value="conditionnel">Conditionnel présent</option>
      <option value="subjonctif">Subjonctif présent</option>
      <option value="impératif">Impératif</option>
    </select>
    <div class="conj-quick">
      <button class="chip" data-jump-verb="être">être</button>
      <button class="chip" data-jump-verb="avoir">avoir</button>
      <button class="chip" data-jump-verb="aller">aller</button>
      <button class="chip" data-jump-verb="faire">faire</button>
      <button class="chip" data-jump-verb="pouvoir">pouvoir</button>
      <button class="chip" data-jump-verb="vouloir">vouloir</button>
      <button class="chip" data-jump-verb="devoir">devoir</button>
      <button class="chip" data-jump-verb="savoir">savoir</button>
    </div>
  </div>

  <div class="conj-readout" id="conj-readout" aria-live="polite">
    <!-- Filled by tools.js -->
  </div>

  <details class="traj-explain">
    <summary>Why these 32 verbs?</summary>
    <p>Lonsdale &amp; Le Bras (2009) corpus frequency for written French puts <em>être · avoir · faire · dire · pouvoir · aller · voir · savoir · vouloir · venir</em> as the top ten verbs by token count — they carry roughly 25 % of all verb tokens. The remaining 22 here are the high-frequency irregulars (<em>devoir, falloir, mettre, prendre, …</em>) plus the two model regulars (<em>parler, finir</em>) so an -er and -ir paradigm is always one click away. The conjugations encode the orthographic alternations the B1→B2 jump demands.</p>
  </details>
</section>

## ② Number-to-French — the part of CO that ambushes you {#numbers}

> Single-play CO dictée routinely embeds <em>"trois cent quatre-vingt-douze euros et soixante-quinze centimes"</em> in the middle of an otherwise A2-easy passage. The trick is not vocabulary — it's parsing the breath group. Punch in a number; see how it's pronounced.

<section class="learn-card tool-card" data-tool="num">
  <div class="num-controls">
    <label for="num-input" class="nclc-control-label">Number (0 – 1 000 000)</label>
    <input type="number" id="num-input" class="select" min="0" max="1000000" step="1" value="1789" inputmode="numeric" />
    <div class="num-quick">
      <button class="chip" data-jump-num="80">80</button>
      <button class="chip" data-jump-num="91">91</button>
      <button class="chip" data-jump-num="99">99</button>
      <button class="chip" data-jump-num="100">100</button>
      <button class="chip" data-jump-num="200">200</button>
      <button class="chip" data-jump-num="1789">1789</button>
      <button class="chip" data-jump-num="2026">2026</button>
      <button class="chip" data-jump-num="1000000">1 M</button>
    </div>
  </div>

  <div class="num-readout" id="num-readout" aria-live="polite">
    <!-- Filled by tools.js -->
  </div>

  <p class="demo-note">The conversion follows standard <em>français de France</em> spelling (post-1990 rectifications: hyphens between every part of a compound number). Belgian/Swiss <em>septante / nonante</em> would also be valid — they're listed under each output for awareness, since the TCF accepts standard-French answers.</p>
</section>

## ③ Dates &amp; time — month-day, ordinals, 24-hour clock {#dates}

> Drop a date and a time; get both written and spoken French. Most CO passages embed at least one date or time. Note the <em>le premier</em> (only "1st" is ordinal in French dates) — every other day is cardinal.

<section class="learn-card tool-card" data-tool="dt">
  <div class="dt-controls">
    <label for="dt-date" class="nclc-control-label">Date</label>
    <input type="date" id="dt-date" class="select" />
    <label for="dt-time" class="nclc-control-label">Time (24 h)</label>
    <input type="time" id="dt-time" class="select" />
  </div>
  <div class="dt-readout" id="dt-readout" aria-live="polite">
    <!-- Filled by tools.js -->
  </div>
</section>

## ④ Accent helper — type without the layout-switch detour {#accents}

> Six rows of mode-switching tax your brain when you're writing under the EE clock. Click an accented letter (or use the keyboard shortcut) to insert it into the scratchpad below, then paste into the writing pad. The browser's clipboard stays out of the way.

<section class="learn-card tool-card" data-tool="acc">
  <div class="acc-grid">
    <button class="acc-key" data-ch="à">à</button>
    <button class="acc-key" data-ch="â">â</button>
    <button class="acc-key" data-ch="ä">ä</button>
    <button class="acc-key" data-ch="ç">ç</button>
    <button class="acc-key" data-ch="é">é</button>
    <button class="acc-key" data-ch="è">è</button>
    <button class="acc-key" data-ch="ê">ê</button>
    <button class="acc-key" data-ch="ë">ë</button>
    <button class="acc-key" data-ch="î">î</button>
    <button class="acc-key" data-ch="ï">ï</button>
    <button class="acc-key" data-ch="ô">ô</button>
    <button class="acc-key" data-ch="ö">ö</button>
    <button class="acc-key" data-ch="ù">ù</button>
    <button class="acc-key" data-ch="û">û</button>
    <button class="acc-key" data-ch="ü">ü</button>
    <button class="acc-key" data-ch="œ">œ</button>
    <button class="acc-key" data-ch="æ">æ</button>
    <button class="acc-key" data-ch="«">«</button>
    <button class="acc-key" data-ch="»">»</button>
    <button class="acc-key" data-ch="’">’</button>
    <button class="acc-key" data-ch="…">…</button>
    <button class="acc-key" data-ch=" ">␣</button>
  </div>
  <label for="acc-pad" class="nclc-control-label" style="margin-top:14px;">Scratchpad</label>
  <textarea id="acc-pad" class="dict-input" rows="3" placeholder="Tapez ici, ou cliquez les touches accentuées au-dessus…" lang="fr"></textarea>
  <div class="acc-actions">
    <button class="btn btn-primary" id="acc-copy">Copy to clipboard</button>
    <button class="btn btn-secondary" id="acc-clear">Clear</button>
    <span class="dict-meta" id="acc-meta">0 characters</span>
  </div>
  <p class="demo-note"><strong>OS shortcuts</strong> (no extension needed): macOS — <span class="kbd">⌥</span>+<span class="kbd">E</span> then <span class="kbd">E</span> = é. Windows — install the FR-CA keyboard, then right <span class="kbd">Alt</span>+<span class="kbd">'</span> then <span class="kbd">E</span> = é. iOS/Android — long-press the letter. This helper is the fallback for browsers where IME composition lags.</p>
</section>

## ⑤ IPA phoneme chart for French {#ipa}

> The 36 phonemes of standard French. Click any tile to hear it spoken (uses your device's French TTS — same caveats as the dictée). Hover (or focus) for an example word.

<section class="learn-card tool-card" data-tool="ipa">
  <div class="ipa-section">
    <h4>Voyelles orales (12)</h4>
    <div class="ipa-grid" id="ipa-vowels"></div>
  </div>
  <div class="ipa-section">
    <h4>Voyelles nasales (4)</h4>
    <div class="ipa-grid" id="ipa-vowels-nasal"></div>
  </div>
  <div class="ipa-section">
    <h4>Semi-voyelles (3)</h4>
    <div class="ipa-grid" id="ipa-semivowels"></div>
  </div>
  <div class="ipa-section">
    <h4>Consonnes (17)</h4>
    <div class="ipa-grid" id="ipa-consonants"></div>
  </div>
  <p class="demo-note">IPA values from Tranel (1987); example minimal pairs from Walker (2001). TTS rendering depends on the voice quality on your OS — Apple's <em>Amélie</em> (fr-CA) is the cleanest distinction of <em>/ɛ̃/</em> vs <em>/œ̃/</em>; Microsoft's older voices merge them.</p>
</section>

## ⑥ Gender helper — pattern-based, not memorised {#gender}

> French nouns force a gender choice on every article and many adjective endings. ~80 % of nouns follow predictable suffix patterns — type a noun (or paste a sentence) and the helper highlights probable gender for each token, with confidence. Override list covers the high-frequency exceptions (<em>le silence, le génie, la peau, …</em>).

<section class="learn-card tool-card" data-tool="gen">
  <label for="gen-input" class="nclc-control-label">Noun or short phrase</label>
  <input type="text" id="gen-input" class="select" placeholder="e.g. citoyenneté, voyage, problème…" lang="fr" autocomplete="off" />
  <div class="num-quick">
    <button class="chip" data-jump-gen="citoyenneté">citoyenneté</button>
    <button class="chip" data-jump-gen="voyage">voyage</button>
    <button class="chip" data-jump-gen="problème">problème</button>
    <button class="chip" data-jump-gen="silence">silence</button>
    <button class="chip" data-jump-gen="peau">peau</button>
    <button class="chip" data-jump-gen="bonheur">bonheur</button>
    <button class="chip" data-jump-gen="entreprise">entreprise</button>
    <button class="chip" data-jump-gen="système">système</button>
  </div>
  <div class="gen-readout" id="gen-readout" aria-live="polite">
    <!-- Filled by tools.js -->
  </div>
  <p class="demo-note">Suffix patterns by frequency: <em>-tion, -sion, -té, -ette, -ence, -ance, -ure, -ée, -eur</em> → typically feminine. <em>-age, -ment, -isme, -eau, -ier, -in, -eur (agent), -on</em> → typically masculine. The helper applies these and then overrides with the 80-word exception list (e.g. <em>silence</em> looks like <em>-ence</em> but is masculine). For ambiguous cases it reports both with confidence &lt; 70%.</p>
</section>

## ⑦ Liaison preview — where sound bridges between words {#liaison}

> French liaison rules trip up listening because they're invisible in writing. Paste a short phrase; the preview marks every <strong>obligatory</strong>, <strong>optional</strong>, and <strong>forbidden</strong> liaison with the consonant that surfaces (often a silent <em>s/t/n</em> reactivated as /z/, /t/, /n/). Useful before recording yourself or after missing a dictée word.

<section class="learn-card tool-card" data-tool="liz">
  <label for="liz-input" class="nclc-control-label">Phrase</label>
  <textarea id="liz-input" class="dict-input" rows="2" lang="fr" autocapitalize="sentences" autocomplete="off" placeholder="Tapez une phrase courte. Par exemple : « Les enfants vont en classe. »"></textarea>
  <div class="num-quick">
    <button class="chip" data-jump-liz="Les enfants vont en classe.">Les enfants vont en classe.</button>
    <button class="chip" data-jump-liz="Nous avons un ami.">Nous avons un ami.</button>
    <button class="chip" data-jump-liz="Les hommes et les femmes.">Les hommes et les femmes.</button>
    <button class="chip" data-jump-liz="Vous êtes en avance.">Vous êtes en avance.</button>
    <button class="chip" data-jump-liz="C'est un beau hibou.">C'est un beau hibou.</button>
  </div>
  <div class="liz-readout" id="liz-readout" aria-live="polite">
    <!-- Filled by tools.js -->
  </div>
  <p class="demo-note">Obligatoires (in green): article + noun (<em>les_amis</em>), pronoun + verb (<em>nous_avons</em>), monosyllabic prepositions (<em>en_avance</em>). Interdites (in red): before an <em>h aspiré</em> (<em>les / hibou</em>, no liaison), after <em>et</em>, before some proper nouns. Facultatives (in yellow): in careful speech but commonly dropped (<em>vous êtes_arrivés</em>). The rule list is heuristic and won't cover every edge case — but it gets the 90 % that show up in TCF dictées.</p>
</section>

## ⑧ Score converter — NCLC ↔ CEFR ↔ TCF raw {#converter}

> The single most common question I get from learners: <em>"My CO is 415 — is that NCLC 7?"</em> This widget answers it both ways. Pick your input scale (NCLC, CEFR, TCF reception /699, or TCF production 1–6), and see all four equivalents at once. The source-of-truth scale is highlighted; the rest are derived from the publicly documented IRCC equivalency chart.

<section class="learn-card conv-card" data-tool="conv" id="conv-card">
  <p class="muted">Loading converter…</p>
</section>

<p class="demo-note">The mapping is the public IRCC reference chart. Real TCF scoring is administered and certified by FEI. Use this as orientation when reading a score report (e.g. confirming your CE 470 is enough for NCLC 8) or when reading a public corpus that labels passages by CEFR (e.g. a B2 passage maps to NCLC 8). For the system's own use of NCLC bands and credible intervals, see <a href="{{ '/PEDAGOGY/' | relative_url }}">PEDAGOGY</a>.</p>

---

## Where this fits in the 12-week plan

These tools aren't on the daily plan because they're <strong>look-ups</strong>, not training. The planner says: when you hit a verb you can't conjugate during a writing drill, open the conjugator in a second tab; when you hear a number you can't parse during the dictée, run it through the number-to-French converter once and move on. The training is in [/practice/]({{ '/practice/' | relative_url }}); these are the references that make a 25-minute session not stall on a mechanics blocker.
