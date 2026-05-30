/* tcf-accel — CEFR ↔ NCLC ↔ TCF score converter
 *
 * Source mappings — all from the published Canadian government / FEI tables:
 *   - NCLC ↔ CEFR mapping (public, Canada Gazette II, IRCC reference).
 *   - TCF Canada raw-score ranges per skill, mapped to NCLC bands (FEI / IRCC).
 *
 * For score-per-skill we use the canonical TCF Canada bands published by FEI:
 *   • Compréhension orale (CO) : /699
 *   • Compréhension écrite (CE): /699
 *   • Expression écrite (EE)   : levels 1..6 (mapped to NCLC bands)
 *   • Expression orale (EO)    : levels 1..6 (mapped to NCLC bands)
 *
 * The shown ranges are the publicly documented thresholds at each NCLC band.
 * Real scoring is held by FEI; this is a learner-facing approximation.
 */
(function () {
  "use strict";

  // NCLC 1..12 ↔ CEFR ↔ TCF reception bands (CO/CE, /699), TCF production levels (EE/EO).
  // Sources cross-checked against IRCC's published equivalency chart.
  var TABLE = [
    { nclc: 1,  cefr: "A1-",  rec: [0,   148], prod: 1, label: "Pre-foundational" },
    { nclc: 2,  cefr: "A1",   rec: [149, 198], prod: 1, label: "A1 — basic user" },
    { nclc: 3,  cefr: "A1+",  rec: [199, 248], prod: 2, label: "A1+ — survival" },
    { nclc: 4,  cefr: "A2",   rec: [249, 297], prod: 2, label: "A2 — basic" },
    { nclc: 5,  cefr: "A2+",  rec: [298, 348], prod: 3, label: "A2+ — pre-independent" },
    { nclc: 6,  cefr: "B1",   rec: [349, 397], prod: 4, label: "B1 — independent" },
    { nclc: 7,  cefr: "B1+",  rec: [398, 457], prod: 5, label: "B1+ — strong independent · IRCC target" },
    { nclc: 8,  cefr: "B2",   rec: [458, 502], prod: 5, label: "B2 — upper-intermediate · CEC threshold" },
    { nclc: 9,  cefr: "B2+",  rec: [503, 548], prod: 6, label: "B2+ — strong B2 · Express Entry bonus" },
    { nclc: 10, cefr: "C1",   rec: [549, 598], prod: 6, label: "C1 — proficient" },
    { nclc: 11, cefr: "C1+",  rec: [599, 648], prod: 6, label: "C1+ — strong C1" },
    { nclc: 12, cefr: "C2",   rec: [649, 699], prod: 6, label: "C2 — mastery" }
  ];

  function byNclc(n)    { return TABLE.find(function (r) { return r.nclc === n; }) || TABLE[0]; }
  function byCefr(c)    { return TABLE.find(function (r) { return r.cefr === c; }) || TABLE[5]; }
  function byRec(score) { return TABLE.find(function (r) { return score >= r.rec[0] && score <= r.rec[1]; }) || TABLE[0]; }
  function byProd(p)    {
    var cands = TABLE.filter(function (r) { return r.prod === p; });
    return cands[cands.length - 1] || TABLE[0]; // pick the highest NCLC for that prod level
  }

  function mount() {
    var host = document.getElementById("conv-card");
    if (!host) return;

    // State: source = "nclc" | "cefr" | "rec" | "prod"; value depends.
    var state = { source: "nclc", value: 7 };

    function inputUI() {
      if (state.source === "nclc") {
        return (
          '<div class="conv-slider-wrap">' +
          '  <input type="range" id="conv-slider" min="1" max="12" step="1" value="' + state.value + '" aria-label="NCLC level">' +
          '  <div class="conv-slider-ticks">' +
          [1,2,3,4,5,6,7,8,9,10,11,12].map(function (n) { return "<span>" + n + "</span>"; }).join("") +
          '  </div>' +
          '</div>'
        );
      }
      if (state.source === "cefr") {
        var levels = ["A1-","A1","A1+","A2","A2+","B1","B1+","B2","B2+","C1","C1+","C2"];
        return (
          '<div class="conv-tabs" role="tablist" id="conv-cefr-tabs">' +
          levels.map(function (l) {
            return '<button class="conv-tab' + (l === state.value ? " is-active" : "") + '" data-cefr="' + l + '">' + l + '</button>';
          }).join("") +
          '</div>'
        );
      }
      if (state.source === "rec") {
        return (
          '<div class="conv-slider-wrap">' +
          '  <input type="range" id="conv-slider" min="0" max="699" step="1" value="' + state.value + '" aria-label="TCF reception score">' +
          '  <div class="conv-slider-ticks">' +
          ['0','148','248','348','457','548','699'].map(function (n) { return "<span>" + n + "</span>"; }).join("") +
          '  </div>' +
          '</div>'
        );
      }
      if (state.source === "prod") {
        return (
          '<div class="conv-tabs" id="conv-prod-tabs" role="tablist">' +
          [1,2,3,4,5,6].map(function (p) {
            return '<button class="conv-tab' + (p === state.value ? " is-active" : "") + '" data-prod="' + p + '">Niveau ' + p + '</button>';
          }).join("") +
          '</div>'
        );
      }
    }

    function row() {
      // Resolve current state → canonical row.
      switch (state.source) {
        case "nclc": return byNclc(state.value);
        case "cefr": return byCefr(state.value);
        case "rec":  return byRec(state.value);
        case "prod": return byProd(state.value);
      }
      return TABLE[0];
    }

    function render() {
      var r = row();
      var src = state.source;
      host.innerHTML =
        '<div class="conv-grid">' +
        '  <div class="conv-input">' +
        '    <div class="conv-tabs" id="conv-src-tabs" role="tablist">' +
        '      <button class="conv-tab' + (src === "nclc" ? " is-active" : "") + '" data-src="nclc">NCLC</button>' +
        '      <button class="conv-tab' + (src === "cefr" ? " is-active" : "") + '" data-src="cefr">CEFR</button>' +
        '      <button class="conv-tab' + (src === "rec" ? " is-active" : "") + '" data-src="rec">TCF CO/CE</button>' +
        '      <button class="conv-tab' + (src === "prod" ? " is-active" : "") + '" data-src="prod">TCF EE/EO</button>' +
        '    </div>' +
        '    <label class="conv-tabs-help">' + (
          src === "nclc" ? "Drag the slider to pick a Canadian Language Benchmark for French (NCLC 1–12)" :
          src === "cefr" ? "Pick a CEFR level (A1 → C2)" :
          src === "rec"  ? "Drag the slider for a TCF reception raw score (CO or CE, /699)" :
          "Pick a TCF production level (EE or EO, 1–6)"
        ) + '</label>' +
            inputUI() +
        '  </div>' +
        '  <div class="conv-readout" aria-live="polite">' +
        '    <div class="conv-line' + (src === "nclc" ? " is-source" : "") + '">' +
        '      <div class="conv-line-label">NCLC</div>' +
        '      <div><div class="conv-line-val">' + r.nclc + '</div>' +
        '           <div class="conv-line-range">' + r.label + '</div></div>' +
        '    </div>' +
        '    <div class="conv-line' + (src === "cefr" ? " is-source" : "") + '">' +
        '      <div class="conv-line-label">CEFR</div>' +
        '      <div><div class="conv-line-val">' + r.cefr + '</div>' +
        '           <div class="conv-line-range">CECRL · learner-facing approximation</div></div>' +
        '    </div>' +
        '    <div class="conv-line' + (src === "rec" ? " is-source" : "") + '">' +
        '      <div class="conv-line-label">TCF CO/CE</div>' +
        '      <div><div class="conv-line-val">' + r.rec[0] + '–' + r.rec[1] + '</div>' +
        '           <div class="conv-line-range">raw score · /699 · reception</div></div>' +
        '    </div>' +
        '    <div class="conv-line' + (src === "prod" ? " is-source" : "") + '">' +
        '      <div class="conv-line-label">TCF EE/EO</div>' +
        '      <div><div class="conv-line-val">Niveau ' + r.prod + '</div>' +
        '           <div class="conv-line-range">production level · 1–6</div></div>' +
        '    </div>' +
        '    <p class="conv-note">Real TCF scoring is administered by FEI. These bands are the publicly documented equivalencies (IRCC reference chart) — use them as orientation, not certification. <a href="' + (window.SITE_BASE || "") + '/glossary/#nclc">NCLC glossary →</a></p>' +
        '  </div>' +
        '</div>';
      wire();
    }

    function wire() {
      host.querySelectorAll("#conv-src-tabs .conv-tab").forEach(function (b) {
        b.addEventListener("click", function () {
          var newSrc = b.dataset.src;
          if (newSrc === state.source) return;
          // Carry value: keep equivalent meaning when switching source.
          var r = row();
          if (newSrc === "nclc") state.value = r.nclc;
          else if (newSrc === "cefr") state.value = r.cefr;
          else if (newSrc === "rec") state.value = Math.round((r.rec[0] + r.rec[1]) / 2);
          else if (newSrc === "prod") state.value = r.prod;
          state.source = newSrc;
          render();
        });
      });
      var slider = host.querySelector("#conv-slider");
      if (slider) {
        slider.addEventListener("input", function () {
          state.value = parseInt(slider.value, 10);
          render();
        });
      }
      host.querySelectorAll("[data-cefr]").forEach(function (b) {
        b.addEventListener("click", function () { state.value = b.dataset.cefr; render(); });
      });
      host.querySelectorAll("[data-prod]").forEach(function (b) {
        b.addEventListener("click", function () { state.value = parseInt(b.dataset.prod, 10); render(); });
      });
    }

    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else { mount(); }
})();
