---
layout: default
title: "Try it"
eyebrow: "Interactive demo"
subtitle: "A static, in-browser model of the system's load-bearing UI surfaces — the readiness gate, the credible interval renderer, and the bottleneck allocator. No backend; the logic runs in your browser."
scripts:
  - /assets/js/demo.js
---

<div class="callout callout-info">
  <p class="callout-title">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
    This is a faithful in-browser model
  </p>
  <p>The three demos below run the same logic as the production system — <a href="{{ '/PEDAGOGY/' | relative_url }}#5-the-readiness-gate">readiness gate (ADR-045)</a>, <a href="{{ '/ARCHITECTURE/' | relative_url }}#4-the-estimator-bayesian-nclc-posterior">credible interval (ADR-025)</a>, and <a href="{{ '/ARCHITECTURE/' | relative_url }}#3-the-planner-pipeline">bottleneck allocator (ADR-027)</a> — re-implemented in vanilla JS so it works without a backend. Move the sliders; the renderings update live.</p>
</div>

## 1. Readiness gate

> ADR-045: 🟢 requires **all four skills confident** AND **two consecutive canonical mocks green**. This widget shows what the production system shows, given the inputs on the left.

<section class="demo-grid">
  <div class="demo-panel">
    <h3>Inputs</h3>
    <p class="demo-sub">Your four NCLC posteriors and your recent mock streak.</p>

    <div class="slider-row">
      <label for="r-co">CO</label>
      <input type="range" id="r-co" min="3" max="11" step="0.1" value="7.2" data-skill="CO" />
      <span class="val" data-val="r-co">7.2</span>
    </div>
    <div class="slider-row">
      <label for="r-ce">CE</label>
      <input type="range" id="r-ce" min="3" max="11" step="0.1" value="7.6" data-skill="CE" />
      <span class="val" data-val="r-ce">7.6</span>
    </div>
    <div class="slider-row">
      <label for="r-ee">EE</label>
      <input type="range" id="r-ee" min="3" max="11" step="0.1" value="7.1" data-skill="EE" />
      <span class="val" data-val="r-ee">7.1</span>
    </div>
    <div class="slider-row">
      <label for="r-eo">EO</label>
      <input type="range" id="r-eo" min="3" max="11" step="0.1" value="6.9" data-skill="EO" />
      <span class="val" data-val="r-eo">6.9</span>
    </div>

    <hr style="margin: 18px 0; border-top: 1px solid var(--rule);" />

    <div class="slider-row">
      <label for="r-target">Target</label>
      <input type="range" id="r-target" min="5" max="11" step="1" value="7" />
      <span class="val" data-val="r-target">NCLC 7</span>
    </div>
    <div class="slider-row">
      <label for="r-mocks">Mocks 🟢</label>
      <input type="range" id="r-mocks" min="0" max="3" step="1" value="2" />
      <span class="val" data-val="r-mocks">2</span>
    </div>
    <div class="slider-row">
      <label for="r-confident">Confident</label>
      <input type="range" id="r-confident" min="0" max="4" step="1" value="4" />
      <span class="val" data-val="r-confident">4 / 4</span>
    </div>
  </div>

  <div class="demo-panel">
    <h3>Readiness signal</h3>
    <p class="demo-sub">What the production widget would render in this state.</p>

    <div class="demo-readiness" id="demo-readiness">
      <span class="light" id="demo-readiness-light"></span>
      <p class="verdict" id="demo-readiness-verdict"></p>
      <p class="reason" id="demo-readiness-reason"></p>
    </div>

    <p class="demo-note">Rule (ADR-045): light = <strong>READY (🟢)</strong> only if min(posteriors) ≥ target AND mocks_green ≥ 2 AND all four confident. Otherwise the widget shows the most informative degraded state and offers the "see your priority drills" CTA — never the "book your exam" CTA.</p>
  </div>
</section>

## 2. Credible interval renderer

> ADR-025: the system never shows a bare NCLC number without its CI. `<CredibleInterval />` is the only component allowed to render an NCLC value in the entire web app, enforced by the `no-bare-nclc` ESLint rule.

<section class="demo-grid">
  <div class="demo-panel">
    <h3>Inputs</h3>
    <p class="demo-sub">Posterior mean, variance, observation count.</p>

    <div class="slider-row">
      <label for="ci-mean">Mean</label>
      <input type="range" id="ci-mean" min="3" max="11" step="0.1" value="7.4" />
      <span class="val" data-val="ci-mean">7.4</span>
    </div>
    <div class="slider-row">
      <label for="ci-var">Variance</label>
      <input type="range" id="ci-var" min="0.05" max="2.0" step="0.05" value="0.3" />
      <span class="val" data-val="ci-var">0.30</span>
    </div>
    <div class="slider-row">
      <label for="ci-nobs">n_obs</label>
      <input type="range" id="ci-nobs" min="0" max="120" step="1" value="48" />
      <span class="val" data-val="ci-nobs">48</span>
    </div>
    <div class="slider-row">
      <label for="ci-target">Target</label>
      <input type="range" id="ci-target" min="5" max="11" step="1" value="7" />
      <span class="val" data-val="ci-target">NCLC 7</span>
    </div>
  </div>

  <div class="demo-panel">
    <h3>Render</h3>
    <p class="demo-sub">95% credible interval on a band-coded scale.</p>

    <div class="demo-ci" id="demo-ci">
      <div class="demo-ci-head">
        <h4 id="demo-ci-headline">NCLC 7</h4>
        <span class="ci-text" id="demo-ci-text">[6, 8]</span>
      </div>
      <div class="demo-ci-track">
        <span class="scale-bg"></span>
        <span class="demo-ci-ci" id="demo-ci-ci"></span>
        <span class="demo-ci-mark" id="demo-ci-mark"></span>
        <span class="demo-ci-target" id="demo-ci-target"></span>
      </div>
    </div>

    <div id="demo-ci-conf" style="margin-top: 24px;"></div>
    <p class="demo-note">Confidence gate (ADR-025): a posterior is <code>confident=True</code> iff <strong>n_obs ≥ 40</strong> AND <strong>variance ≤ 0.4</strong> AND ≥ 3 difficulty bands have been seen (the third clause requires session data we don't have here, so this demo gates on the first two only).</p>
  </div>
</section>

## 3. Bottleneck allocator

> ADR-027: per-skill daily minutes ∝ max(ε, (target − mean)²) · β<sub>skill</sub>, where β<sub>EE</sub>=1.4 and β<sub>EO</sub>=1.5 over-weight the production skills. Production-skill floor of 10 min per skill.

<section class="demo-grid">
  <div class="demo-panel">
    <h3>Inputs</h3>
    <p class="demo-sub">Daily minute budget + current posteriors + target.</p>

    <div class="slider-row">
      <label for="a-budget">Budget</label>
      <input type="range" id="a-budget" min="60" max="240" step="10" value="150" />
      <span class="val" data-val="a-budget">150 min</span>
    </div>
    <div class="slider-row">
      <label for="a-co">CO</label>
      <input type="range" id="a-co" min="3" max="11" step="0.1" value="6.5" />
      <span class="val" data-val="a-co">6.5</span>
    </div>
    <div class="slider-row">
      <label for="a-ce">CE</label>
      <input type="range" id="a-ce" min="3" max="11" step="0.1" value="6.5" />
      <span class="val" data-val="a-ce">6.5</span>
    </div>
    <div class="slider-row">
      <label for="a-ee">EE</label>
      <input type="range" id="a-ee" min="3" max="11" step="0.1" value="4.5" />
      <span class="val" data-val="a-ee">4.5</span>
    </div>
    <div class="slider-row">
      <label for="a-eo">EO</label>
      <input type="range" id="a-eo" min="3" max="11" step="0.1" value="5.0" />
      <span class="val" data-val="a-eo">5.0</span>
    </div>
    <div class="slider-row">
      <label for="a-target">Target</label>
      <input type="range" id="a-target" min="5" max="11" step="1" value="7" />
      <span class="val" data-val="a-target">NCLC 7</span>
    </div>
  </div>

  <div class="demo-panel">
    <h3>Today's plan</h3>
    <p class="demo-sub">10 min/day shadowing reserved (ADR-030), the rest allocated by the bottleneck weighting.</p>

    <div id="demo-alloc"></div>
    <p class="demo-note">Why EE/EO get extra minutes when they're below target: production skills (EE writing, EO speaking) need pushed-output volume to move (Swain 1985 — see <a href="{{ '/PEDAGOGY/' | relative_url }}#1-the-eight-evidence-aligned-sla-principles">PEDAGOGY §1</a>). β=1.4/1.5 is the documented over-weight (ADR-027).</p>
  </div>
</section>

---

## Where the rest of the system lives

This page is what GitHub Pages can do — three pure-function UI surfaces in JS. The rest of the system needs a backend, a queue, a database, and an audio pipeline. Three honest ways to run it:

- **Solo, on your laptop** — `docker compose up`. See [OPERATIONS.md §1](OPERATIONS.md). Cold start under 60 s.
- **On a cloud VM** — Helm chart at `infra/helm/`. Single-tenant per learner at v1.0.
- **Just read the artefacts** — the [signed Launch Readiness Report]({{ '/LAUNCH_READINESS_REPORT/' | relative_url }}), the [pedagogy audit JSON]({{ '/data/audit/phase9/pedagogy_audit.json' | relative_url }}), the [published κ]({{ '/data/calibration/ee.v1.report/' | relative_url }}). Verifiable without running anything.
