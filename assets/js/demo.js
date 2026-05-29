// tcf-accel — interactive demos.
// Vanilla JS implementations of:
//   1. Readiness gate (ADR-045)
//   2. Credible interval renderer (ADR-025)
//   3. Bottleneck allocator (ADR-027)
// Faithful to the production semantics. No backend.

(function () {
  "use strict";

  // ─── 1. Readiness gate (ADR-045) ─────────────────────────────────

  function computeReadiness(posteriors, target, mocksGreen, confidentCount) {
    // Replicates packages/sla/.../planner/readiness.py.
    // States: READY, READY_ONE_MOCK, BORDERLINE, NOT_READY, REGRESSED, INSUFFICIENT_DATA.
    var min = Math.min(posteriors.CO, posteriors.CE, posteriors.EE, posteriors.EO);
    var bottleneck = ["CO", "CE", "EE", "EO"].reduce(function (acc, s) {
      return posteriors[s] < posteriors[acc] ? s : acc;
    });
    var allConfident = confidentCount >= 4;

    if (confidentCount === 0) {
      return {
        light: "gray",
        state: "INSUFFICIENT_DATA",
        verdict: "Not enough data yet.",
        reason: "Take the diagnostic + run drills so the posteriors clear the confidence gate (n_obs ≥ 40, variance ≤ 0.4, ≥ 3 difficulty bands)."
      };
    }
    if (min < target) {
      var gap = (target - min).toFixed(1);
      return {
        light: "red",
        state: "NOT_READY",
        verdict: "Not ready — " + bottleneck + " is " + gap + " NCLC below target.",
        reason: "Focus the next plan cycle on " + bottleneck + ". The system will refuse the booking CTA until all four skills clear target."
      };
    }
    if (!allConfident) {
      return {
        light: "yellow",
        state: "BORDERLINE",
        verdict: "Posterior strong; confidence not yet there.",
        reason: confidentCount + "/4 skills clear the ADR-025 confidence gate. Run more drills across difficulty bands."
      };
    }
    if (mocksGreen === 0) {
      return {
        light: "yellow",
        state: "BORDERLINE",
        verdict: "Posterior says you're there — but no canonical mocks yet.",
        reason: "Run a canonical mock; the readiness gate requires two consecutive 🟢 mocks before the booking CTA appears."
      };
    }
    if (mocksGreen === 1) {
      return {
        light: "yellow",
        state: "READY_ONE_MOCK",
        verdict: "One green canonical mock. Run a second.",
        reason: "ADR-045: 🟢 requires two consecutive canonical mocks at green. Run the second mock in 7–10 days; book after."
      };
    }
    return {
      light: "green",
      state: "READY",
      verdict: "Ready. Book the exam.",
      reason: mocksGreen + " consecutive canonical mocks at green. All four skills posterior-confident. Min skill (" + bottleneck + ") at " + min.toFixed(1) + " ≥ target " + target + "."
    };
  }

  function renderReadiness() {
    var inputs = {
      CO: parseFloat(document.getElementById("r-co").value),
      CE: parseFloat(document.getElementById("r-ce").value),
      EE: parseFloat(document.getElementById("r-ee").value),
      EO: parseFloat(document.getElementById("r-eo").value)
    };
    var target = parseInt(document.getElementById("r-target").value, 10);
    var mocks = parseInt(document.getElementById("r-mocks").value, 10);
    var confident = parseInt(document.getElementById("r-confident").value, 10);

    document.querySelector('[data-val="r-co"]').textContent = inputs.CO.toFixed(1);
    document.querySelector('[data-val="r-ce"]').textContent = inputs.CE.toFixed(1);
    document.querySelector('[data-val="r-ee"]').textContent = inputs.EE.toFixed(1);
    document.querySelector('[data-val="r-eo"]').textContent = inputs.EO.toFixed(1);
    document.querySelector('[data-val="r-target"]').textContent = "NCLC " + target;
    document.querySelector('[data-val="r-mocks"]').textContent = mocks;
    document.querySelector('[data-val="r-confident"]').textContent = confident + " / 4";

    var r = computeReadiness(inputs, target, mocks, confident);
    var box = document.getElementById("demo-readiness");
    var light = document.getElementById("demo-readiness-light");
    var verdict = document.getElementById("demo-readiness-verdict");
    var reason = document.getElementById("demo-readiness-reason");

    box.classList.remove("is-green", "is-yellow", "is-red", "is-gray");
    box.classList.add("is-" + r.light);
    var glyph = r.light === "green" ? "🟢" : r.light === "yellow" ? "🟡" : r.light === "red" ? "🔴" : "⚪";
    var color = r.light === "green" ? "var(--success)" : r.light === "yellow" ? "var(--warn)" : r.light === "red" ? "var(--danger)" : "var(--ink-muted)";
    light.innerHTML = '<span class="lamp" style="color:' + color + '"></span>' + glyph + ' ' + r.state;
    light.style.color = color;
    verdict.textContent = r.verdict;
    reason.textContent = r.reason;
  }

  ["r-co", "r-ce", "r-ee", "r-eo", "r-target", "r-mocks", "r-confident"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("input", renderReadiness);
  });
  if (document.getElementById("demo-readiness")) renderReadiness();

  // ─── 2. Credible interval (ADR-025) ──────────────────────────────

  function clip(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

  function isConfident(variance, nobs) {
    // Two-of-three (we can't model band-spread without session data).
    return nobs >= 40 && variance <= 0.4;
  }

  function renderCi() {
    var mean = parseFloat(document.getElementById("ci-mean").value);
    var variance = parseFloat(document.getElementById("ci-var").value);
    var nobs = parseInt(document.getElementById("ci-nobs").value, 10);
    var target = parseInt(document.getElementById("ci-target").value, 10);
    var stddev = Math.sqrt(Math.max(variance, 0));

    document.querySelector('[data-val="ci-mean"]').textContent = mean.toFixed(1);
    document.querySelector('[data-val="ci-var"]').textContent = variance.toFixed(2);
    document.querySelector('[data-val="ci-nobs"]').textContent = nobs;
    document.querySelector('[data-val="ci-target"]').textContent = "NCLC " + target;

    var lo = clip(Math.floor(mean - 1.96 * stddev), 1, 12);
    var hi = clip(Math.ceil(mean + 1.96 * stddev), 1, 12);
    var confident = isConfident(variance, nobs);

    var headline = document.getElementById("demo-ci-headline");
    var text = document.getElementById("demo-ci-text");
    if (confident) {
      headline.textContent = "NCLC " + Math.round(mean);
      text.textContent = "[" + lo + ", " + hi + "]";
    } else {
      headline.innerHTML = '<span style="color: var(--ink-muted);">NCLC ?</span>';
      text.textContent = "needs more evidence";
    }

    // Position on the 1..12 scale.
    function pct(v) { return ((clip(v, 1, 12) - 1) / 11) * 100; }
    document.getElementById("demo-ci-mark").style.left = "calc(" + pct(mean) + "% - 1.5px)";
    document.getElementById("demo-ci-ci").style.left = pct(lo) + "%";
    document.getElementById("demo-ci-ci").style.width = (pct(hi) - pct(lo)) + "%";
    document.getElementById("demo-ci-target").style.left = "calc(" + pct(target) + "% - 1px)";

    var conf = document.getElementById("demo-ci-conf");
    var pillClass = confident ? "status-ok" : "status-warn";
    var pillText = confident ? "✓ confident=True" : "✗ confident=False";
    conf.innerHTML =
      '<div style="display:flex; flex-direction:column; gap:8px;">' +
        '<div><span class="status-pill ' + pillClass + '">' + pillText + '</span></div>' +
        '<div style="font-size:var(--fs-xs); color:var(--ink-muted); font-family: var(--font-mono);">' +
          '  variance ' + variance.toFixed(2) + ' ' + (variance <= 0.4 ? '≤' : '>') + ' 0.4 · n_obs ' + nobs + ' ' + (nobs >= 40 ? '≥' : '<') + ' 40' +
        '</div>' +
      '</div>';
  }

  ["ci-mean", "ci-var", "ci-nobs", "ci-target"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("input", renderCi);
  });
  if (document.getElementById("demo-ci")) renderCi();

  // ─── 3. Bottleneck allocator (ADR-027) ───────────────────────────

  var BETA = { CO: 1.0, CE: 0.9, EE: 1.4, EO: 1.5 };
  var SKILL_ORDER = ["CO", "CE", "EE", "EO"];
  var FLOOR = 10;
  var EPS = 0.01;
  var SHADOWING = 10; // ADR-030

  function allocate(totalMinutes, posteriors, target) {
    // Reserve shadowing block first (ADR-030).
    var budget = totalMinutes - SHADOWING;
    if (budget < SKILL_ORDER.length * FLOOR) {
      return null;
    }
    var alphas = {};
    var totalAlpha = 0;
    SKILL_ORDER.forEach(function (s) {
      var gap = Math.max(0, target - posteriors[s]);
      var a = Math.max(EPS, gap * gap) * BETA[s];
      alphas[s] = a;
      totalAlpha += a;
    });
    var raw = {};
    SKILL_ORDER.forEach(function (s) {
      raw[s] = budget * alphas[s] / totalAlpha;
    });
    // Enforce floor + integer rounding + absorb residual.
    var out = {};
    var sum = 0;
    SKILL_ORDER.forEach(function (s) {
      out[s] = Math.max(FLOOR, Math.round(raw[s]));
      sum += out[s];
    });
    // Adjust the largest skill to make the sum match.
    var diff = budget - sum;
    if (diff !== 0) {
      var biggest = SKILL_ORDER.reduce(function (acc, s) { return out[s] > out[acc] ? s : acc; });
      out[biggest] = Math.max(FLOOR, out[biggest] + diff);
    }
    return out;
  }

  function renderAllocator() {
    var budget = parseInt(document.getElementById("a-budget").value, 10);
    var posteriors = {
      CO: parseFloat(document.getElementById("a-co").value),
      CE: parseFloat(document.getElementById("a-ce").value),
      EE: parseFloat(document.getElementById("a-ee").value),
      EO: parseFloat(document.getElementById("a-eo").value)
    };
    var target = parseInt(document.getElementById("a-target").value, 10);

    document.querySelector('[data-val="a-budget"]').textContent = budget + " min";
    document.querySelector('[data-val="a-co"]').textContent = posteriors.CO.toFixed(1);
    document.querySelector('[data-val="a-ce"]').textContent = posteriors.CE.toFixed(1);
    document.querySelector('[data-val="a-ee"]').textContent = posteriors.EE.toFixed(1);
    document.querySelector('[data-val="a-eo"]').textContent = posteriors.EO.toFixed(1);
    document.querySelector('[data-val="a-target"]').textContent = "NCLC " + target;

    var box = document.getElementById("demo-alloc");
    var alloc = allocate(budget, posteriors, target);

    if (!alloc) {
      box.innerHTML = '<div class="callout callout-warn"><p class="callout-title">Budget too small</p><p>Minimum budget to satisfy the 10-min shadowing reservation (ADR-030) and the 10-min/skill floor is ' + (SHADOWING + SKILL_ORDER.length * FLOOR) + ' min.</p></div>';
      return;
    }

    // Build the visual.
    var labels = {
      CO: "Compréhension orale",
      CE: "Compréhension écrite",
      EE: "Expression écrite",
      EO: "Expression orale"
    };
    var html = '';
    html += '<div class="hv-skill" style="margin-bottom:10px;">';
    html += '  <div class="hv-skill-head"><span class="hv-skill-name">Shadowing</span><span>ADR-030</span></div>';
    html += '  <div style="display:flex;justify-content:space-between;align-items:baseline;">';
    html += '    <span class="hv-skill-val">' + SHADOWING + ' min</span>';
    html += '    <span style="font-size:var(--fs-xs);color:var(--ink-muted);">reserved before allocator runs</span>';
    html += '  </div>';
    html += '</div>';
    SKILL_ORDER.forEach(function (s) {
      var mins = alloc[s];
      var post = posteriors[s];
      var gap = target - post;
      var pct = (mins / budget) * 100;
      var label = labels[s];
      var betaText = BETA[s] !== 1 ? " · β=" + BETA[s] : "";
      html += '<div class="hv-skill" style="margin-bottom:10px;">';
      html += '  <div class="hv-skill-head"><span class="hv-skill-name">' + s + ' · ' + label + '</span><span>posterior ' + post.toFixed(1) + '</span></div>';
      html += '  <div style="display:flex;justify-content:space-between;align-items:baseline;">';
      html += '    <span class="hv-skill-val">' + mins + ' min</span>';
      html += '    <span style="font-size:var(--fs-xs);color:var(--ink-muted);">';
      if (gap > 0) {
        html += 'gap ' + gap.toFixed(1) + ' to target' + betaText;
      } else {
        html += 'at or above target' + betaText;
      }
      html += '    </span>';
      html += '  </div>';
      html += '  <div class="hv-skill-bar"><span class="hv-skill-bar-ci" style="left:0;width:' + pct + '%"></span></div>';
      html += '</div>';
    });
    var sum = SHADOWING + SKILL_ORDER.reduce(function (a, s) { return a + alloc[s]; }, 0);
    html += '<p class="demo-note" style="margin-top:14px;">Total: <strong>' + sum + ' / ' + budget + ' min</strong>. Bottleneck: <strong>' + SKILL_ORDER.reduce(function (acc, s) { return posteriors[s] < posteriors[acc] ? s : acc; }) + '</strong>.</p>';
    box.innerHTML = html;
  }

  ["a-budget", "a-co", "a-ce", "a-ee", "a-eo", "a-target"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("input", renderAllocator);
  });
  if (document.getElementById("demo-alloc")) renderAllocator();
})();
