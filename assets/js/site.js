/* tcf-accel docs site — global UI:
 *   • Mobile nav toggle
 *   • Theme cycle (auto → light → dark → auto)
 *   • Command palette (Cmd/Ctrl+K) with fuzzy search over pages + actions
 *   • Keyboard shortcut help (?)
 *   • Reading progress bar on long docs
 *   • Auto TOC sidebar on long docs
 *   • Copy-code buttons on <pre> blocks
 *   • PWA service-worker registration
 *   • Toast helper
 */
(function () {
  "use strict";

  /* ───────────── Mobile nav toggle ─────────────────────────── */
  var toggle = document.querySelector(".nav-toggle");
  var menu = document.getElementById("nav-menu");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    menu.addEventListener("click", function (e) {
      if (e.target.closest("a")) {
        menu.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ───────────── Theme cycle ───────────────────────────────── */
  var themeToggle = document.querySelector(".theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme") || "auto";
      var next = current === "auto" ? "light" : current === "light" ? "dark" : "auto";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("tcf-theme", next); } catch (e) {}
      themeToggle.setAttribute("title", "Theme: " + next);
      toast("Theme: " + next);
    });
  }

  /* ───────────── Toast helper ──────────────────────────────── */
  var toastEl = null;
  function toast(msg, ms) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "toast";
      toastEl.setAttribute("role", "status");
      toastEl.setAttribute("aria-live", "polite");
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.classList.add("is-visible");
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(function () { toastEl.classList.remove("is-visible"); }, ms || 1600);
  }
  window.tcfToast = toast;

  /* ───────────── Site base for fetch URLs ──────────────────── */
  // The Jekyll layout already set window.SITE_BASE = "{{ site.baseurl }}".
  // Trust it. Normalize to never end with a trailing slash so concatenation
  // patterns like `SITE_BASE + "/foo/"` always produce a single slash.
  if (typeof window.SITE_BASE === "string") {
    window.SITE_BASE = window.SITE_BASE.replace(/\/+$/, "");
  } else {
    window.SITE_BASE = "";
  }
  function pathJoin(url) {
    // Join SITE_BASE with a site-relative URL, idempotently: if url already
    // starts with the base, don't double-prefix it.
    if (!url) return window.SITE_BASE || "/";
    if (url.indexOf("://") >= 0) return url;
    var base = window.SITE_BASE || "";
    if (base && url.indexOf(base + "/") === 0) return url;
    if (url.charAt(0) !== "/") url = "/" + url;
    return base + url;
  }
  window.tcfPathJoin = pathJoin;

  /* ───────────── Reading progress bar (on prose pages) ─────── */
  var article = document.querySelector(".prose");
  if (article && article.offsetHeight > window.innerHeight * 1.4) {
    var bar = document.createElement("div");
    bar.className = "reading-progress";
    bar.innerHTML = '<div class="reading-progress-fg" id="reading-progress-fg"></div>';
    document.body.appendChild(bar);
    var fg = document.getElementById("reading-progress-fg");
    var rafQueued = false;
    function updateBar() {
      rafQueued = false;
      var top = window.scrollY;
      var docH = document.documentElement.scrollHeight - window.innerHeight;
      var pct = docH > 0 ? Math.max(0, Math.min(100, (top / docH) * 100)) : 0;
      fg.style.width = pct + "%";
    }
    window.addEventListener("scroll", function () {
      if (!rafQueued) { rafQueued = true; requestAnimationFrame(updateBar); }
    }, { passive: true });
    updateBar();
  }

  /* ───────────── Back-to-top button (long prose) ───────────── */
  if (article && article.offsetHeight > window.innerHeight * 1.6) {
    var btt = document.createElement("button");
    btt.type = "button";
    btt.className = "back-to-top";
    btt.setAttribute("aria-label", "Back to top");
    btt.title = "Back to top";
    btt.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    document.body.appendChild(btt);
    btt.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    });
    var bttRaf = false;
    window.addEventListener("scroll", function () {
      if (bttRaf) return;
      bttRaf = true;
      requestAnimationFrame(function () {
        bttRaf = false;
        btt.classList.toggle("is-visible", window.scrollY > window.innerHeight * 0.6);
      });
    }, { passive: true });
  }

  /* ───────────── Copy-code buttons on <pre> ─────────────────── */
  document.querySelectorAll(".prose pre").forEach(function (pre) {
    if (pre.parentElement && pre.parentElement.classList.contains("code-block-wrap")) return;
    var wrap = document.createElement("div");
    wrap.className = "code-block-wrap";
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-code-btn";
    btn.textContent = "Copy";
    btn.setAttribute("aria-label", "Copy code");
    btn.addEventListener("click", function () {
      var txt = pre.innerText;
      try {
        navigator.clipboard.writeText(txt).then(function () {
          btn.classList.add("is-copied");
          btn.textContent = "Copied!";
          setTimeout(function () { btn.classList.remove("is-copied"); btn.textContent = "Copy"; }, 1200);
        });
      } catch (e) {
        window.prompt("Copy code:", txt);
      }
    });
    wrap.appendChild(btn);
  });

  /* ───────────── TOC sidebar (on long prose pages) ─────────── */
  if (article && article.offsetHeight > window.innerHeight * 2) {
    var headings = article.querySelectorAll("h2[id], h3[id], h4[id]");
    if (headings.length >= 4 && window.innerWidth >= 1280) {
      var toc = document.createElement("aside");
      toc.className = "doc-toc";
      toc.setAttribute("aria-label", "Page contents");
      var html = '<h4>On this page</h4><ol>';
      headings.forEach(function (h) {
        var cls = "toc-" + h.tagName.toLowerCase();
        html += '<li><a href="#' + h.id + '" class="' + cls + '">' + h.textContent + "</a></li>";
      });
      html += '</ol>';
      toc.innerHTML = html;
      // Float the TOC to the right of the prose.
      var wrap = document.createElement("div");
      wrap.style.position = "fixed";
      wrap.style.top = "0";
      wrap.style.right = "16px";
      wrap.style.width = "220px";
      wrap.style.height = "100vh";
      wrap.style.pointerEvents = "none";
      wrap.style.zIndex = "5";
      toc.style.pointerEvents = "auto";
      wrap.appendChild(toc);
      document.body.appendChild(wrap);

      var current = null;
      var raf2 = false;
      function updateTocActive() {
        raf2 = false;
        var y = window.scrollY + (parseInt(getComputedStyle(document.documentElement).getPropertyValue("--header-h"), 10) || 64) + 24;
        var active = null;
        for (var i = 0; i < headings.length; i++) {
          var rect = headings[i].getBoundingClientRect();
          var top = rect.top + window.scrollY;
          if (top <= y) active = headings[i];
          else break;
        }
        if (active !== current) {
          current = active;
          toc.querySelectorAll("a").forEach(function (a) { a.classList.remove("is-active"); });
          if (active) {
            var a = toc.querySelector('a[href="#' + active.id + '"]');
            if (a) a.classList.add("is-active");
          }
        }
      }
      window.addEventListener("scroll", function () {
        if (!raf2) { raf2 = true; requestAnimationFrame(updateTocActive); }
      }, { passive: true });
      updateTocActive();
    }
  }

  /* ───────────── Command palette (Cmd/Ctrl+K) ──────────────── */
  // Static command index — always available. Page index is loaded lazily.
  var COMMANDS = [
    { title: "Practice", desc: "Diagnostic, vocab SRS, dictée, writing, reading, conjugation drill", icon: "play", url: "/practice/", group: "Pages", keywords: "drills exercises srs flashcards" },
    { title: "Conjugation drill", desc: "24 verbs × 6 tenses · accent-tolerant grading", icon: "play", url: "/practice/#conjugation", group: "Drills", keywords: "verbs conjugate paradigm subjunctive imparfait conditional drill" },
    { title: "Listening dictée", desc: "Single-play TCF cadence with word-level diff", icon: "play", url: "/practice/#listening", group: "Drills", keywords: "co compréhension orale listening dictation" },
    { title: "Timed writing (EE)", desc: "Real clock + register coach + autosave", icon: "play", url: "/practice/#writing", group: "Drills", keywords: "ee expression écrite essay writing tâche" },
    { title: "Reading speed (CE)", desc: "WPM + comprehension grading", icon: "play", url: "/practice/#reading", group: "Drills", keywords: "ce compréhension écrite reading wpm" },
    { title: "Vocab SRS", desc: "241-card SM-2 deck", icon: "play", url: "/practice/#vocab", group: "Drills", keywords: "srs vocabulary flashcards anki" },
    { title: "Diagnostic placement", desc: "8 calibrated items → per-skill NCLC + CI", icon: "play", url: "/practice/#diagnostic", group: "Drills", keywords: "placement diagnostic nclc" },
    { title: "Learner studio", desc: "NCLC explorer, exam tabs, mock timer, trajectory", icon: "book", url: "/learn/", group: "Pages", keywords: "interactive nclc" },
    { title: "Mechanics toolkit", desc: "Verb conjugator, numbers, dates, accent helper, IPA chart, gender, liaison", icon: "settings", url: "/tools/", group: "Pages", keywords: "conjugation verbes nombres dates ipa accents genre liaison" },
    { title: "Glossary", desc: "Jargon decoder — NCLC, CEFR, FSRS, IRT, FEI, κ, posterior, ADR", icon: "book", url: "/glossary/", group: "Pages", keywords: "definitions terms acronyms" },
    { title: "Try the readiness widget", desc: "Live demo of the readiness gate", icon: "play", url: "/try/", group: "Pages", keywords: "demo readiness gate ci interval" },
    { title: "Limitations", desc: "Twelve things this system does not promise", icon: "warn", url: "/LIMITATIONS/", group: "Pages", keywords: "honesty disclaimers" },
    { title: "Pedagogy dossier", desc: "Eight SLA principles, evidence, receipts", icon: "book", url: "/PEDAGOGY/", group: "Pages", keywords: "pedagogy sla evidence" },
    { title: "Architecture", desc: "Eight surfaces, ADR-indexed", icon: "layers", url: "/ARCHITECTURE/", group: "Pages", keywords: "system design" },
    { title: "Operations runbook", desc: "Self-hosting, env vars, backups", icon: "settings", url: "/OPERATIONS/", group: "Pages", keywords: "ops docker helm" },
    { title: "Learner guide", desc: "12-week journey, week by week", icon: "calendar", url: "/LEARNER_GUIDE/", group: "Pages", keywords: "week plan" },
    { title: "All 48 ADRs", desc: "Architecture decision records", icon: "list", url: "/adrs/", group: "Pages", keywords: "decisions rationale" },
    { title: "Launch Readiness Report (signed)", desc: "12 gates green; bundle SHA-256", icon: "check", url: "/LAUNCH_READINESS_REPORT/", group: "Pages", keywords: "audit verify" },
    { title: "Risk register", desc: "Zero Open; every Accepted has rationale", icon: "warn", url: "/RISK_REGISTER/", group: "Pages", keywords: "risks register" },
    { title: "Changelog", desc: "v1.0.0 → today", icon: "list", url: "/CHANGELOG/", group: "Pages", keywords: "history release" },
    { title: "Security disclosure", desc: "Responsible disclosure process", icon: "shield", url: "/SECURITY/", group: "Pages", keywords: "security cve" },
    { title: "Contributing guide", desc: "How to send a PR", icon: "git", url: "/CONTRIBUTING/", group: "Pages", keywords: "contribute pr" },
    { title: "Search", desc: "Full-text across all docs", icon: "search", url: "/search/", group: "Pages", keywords: "find" },

    { title: "Toggle theme", desc: "Light / dark / auto", icon: "sun", action: "theme", group: "Actions", keywords: "dark light mode" },
    { title: "Show keyboard shortcuts", desc: "Press ? from anywhere", icon: "kbd", action: "help", group: "Actions", keywords: "help kbd hotkeys" },
    { title: "Open GitHub repo", desc: "github.com/bettyguo/tcf", icon: "git", external: "https://github.com/bettyguo/tcf", group: "External", keywords: "github source code" },
    { title: "v1.0.0 release notes", desc: "GitHub release", icon: "git", external: "https://github.com/bettyguo/tcf/releases/tag/v1.0.0", group: "External", keywords: "release notes" }
  ];

  var ICONS = {
    play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5V5a2 2 0 0 1 2-2h12v18H6a2 2 0 0 1-2-1.5z"/><path d="M8 7h8M8 11h8"/></svg>',
    warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>',
    layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
    calendar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/></svg>',
    list: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
    shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    git: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M6 15V9a6 6 0 0 1 12 0v0"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
    sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/></svg>',
    kbd: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M6 14h12"/></svg>'
  };

  var palette = null;
  var paletteItems = [];
  var activeIdx = 0;
  var pageIndex = null;
  var pageIndexLoading = false;

  function loadPageIndex() {
    if (pageIndex || pageIndexLoading) return;
    pageIndexLoading = true;
    var url = (window.SITE_BASE || "") + "/search-index.json";
    fetch(url, { cache: "force-cache" }).then(function (r) { return r.json(); }).then(function (raw) {
      pageIndex = raw.map(function (p) { return { title: p.title, url: p.url, desc: p.excerpt || "", group: "Doc", body: (p.body || "").slice(0, 1000) }; });
    }).catch(function () { pageIndex = []; });
  }

  function scoreItem(item, q) {
    if (!q) return 0;
    var t = (item.title || "").toLowerCase();
    var d = (item.desc || "").toLowerCase();
    var k = (item.keywords || "").toLowerCase();
    var ql = q.toLowerCase();
    if (t.indexOf(ql) >= 0) return 100 - t.indexOf(ql);
    if (k.indexOf(ql) >= 0) return 60;
    if (d.indexOf(ql) >= 0) return 40;
    // Fuzzy match: every char of q appears in t in order.
    var i = 0;
    for (var j = 0; j < t.length && i < ql.length; j++) {
      if (t[j] === ql[i]) i++;
    }
    if (i === ql.length) return 20;
    return 0;
  }

  function openPalette() {
    if (palette) return;
    palette = document.createElement("div");
    palette.className = "cmdk-backdrop";
    palette.innerHTML =
      '<div class="cmdk-panel" role="dialog" aria-label="Command palette">' +
      '  <div class="cmdk-input-wrap">' +
      '    <span class="cmdk-input-icon">' + ICONS.search + '</span>' +
      '    <input class="cmdk-input" type="text" placeholder="Search docs or jump to a page…" autocomplete="off" />' +
      '    <span class="cmdk-hint"><span class="kbd">esc</span></span>' +
      '  </div>' +
      '  <div class="cmdk-results" id="cmdk-results" role="listbox"></div>' +
      '  <div class="cmdk-footer"><span><span class="kbd">↑↓</span> navigate</span><span><span class="kbd">⏎</span> open</span><span><span class="kbd">esc</span> close</span></div>' +
      '</div>';
    document.body.appendChild(palette);
    var input = palette.querySelector(".cmdk-input");
    var results = palette.querySelector("#cmdk-results");

    function render() {
      var q = input.value.trim();
      var pool = COMMANDS.concat(pageIndex || []);
      var scored = pool.map(function (it) { return { item: it, score: q ? scoreItem(it, q) : (it.group === "Pages" ? 1 : 0) }; })
        .filter(function (x) { return q ? x.score > 0 : true; });
      scored.sort(function (a, b) { return b.score - a.score; });
      paletteItems = scored.slice(0, 20).map(function (x) { return x.item; });
      activeIdx = 0;
      if (!paletteItems.length) {
        results.innerHTML = '<p class="cmdk-empty">No matches. Try a broader term.</p>';
        return;
      }
      var groups = {};
      paletteItems.forEach(function (it) {
        var g = it.group || "Other";
        if (!groups[g]) groups[g] = [];
        groups[g].push(it);
      });
      var html = "";
      Object.keys(groups).forEach(function (g) {
        html += '<p class="cmdk-group-title">' + g + '</p>';
        groups[g].forEach(function (it) {
          var idx = paletteItems.indexOf(it);
          var icon = ICONS[it.icon || "list"] || ICONS.list;
          html += '<div class="cmdk-item' + (idx === activeIdx ? " is-active" : "") + '" data-idx="' + idx + '" role="option">' +
            '<span class="cmdk-item-icon">' + icon + '</span>' +
            '<div><div class="cmdk-item-title">' + it.title + '</div>' +
            (it.desc ? '<div class="cmdk-item-desc">' + it.desc + '</div>' : '') + '</div>' +
            (it.external ? '<span class="cmdk-item-meta">↗</span>' : '<span class="cmdk-item-meta">' + (it.url || "") + '</span>') +
            '</div>';
        });
      });
      results.innerHTML = html;
      results.querySelectorAll(".cmdk-item").forEach(function (el) {
        el.addEventListener("click", function () { exec(parseInt(el.dataset.idx, 10)); });
        el.addEventListener("mouseenter", function () {
          activeIdx = parseInt(el.dataset.idx, 10);
          results.querySelectorAll(".cmdk-item").forEach(function (e2) { e2.classList.toggle("is-active", parseInt(e2.dataset.idx, 10) === activeIdx); });
        });
      });
    }
    function updateActive() {
      results.querySelectorAll(".cmdk-item").forEach(function (el) {
        el.classList.toggle("is-active", parseInt(el.dataset.idx, 10) === activeIdx);
      });
      var act = results.querySelector(".cmdk-item.is-active");
      if (act) act.scrollIntoView({ block: "nearest" });
    }
    function exec(idx) {
      var it = paletteItems[idx];
      if (!it) return;
      closePalette();
      if (it.action === "theme") { themeToggle && themeToggle.click(); return; }
      if (it.action === "help") { showHelpModal(); return; }
      if (it.external) { window.open(it.external, "_blank", "noopener"); return; }
      if (it.url) window.location.href = pathJoin(it.url);
    }

    input.addEventListener("input", render);
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); activeIdx = Math.min(paletteItems.length - 1, activeIdx + 1); updateActive(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); activeIdx = Math.max(0, activeIdx - 1); updateActive(); }
      else if (e.key === "Enter") { e.preventDefault(); exec(activeIdx); }
      else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
    });
    palette.addEventListener("click", function (e) { if (e.target === palette) closePalette(); });
    loadPageIndex();
    render();
    setTimeout(function () { input.focus(); }, 30);
  }
  function closePalette() {
    if (!palette) return;
    palette.remove(); palette = null;
  }

  /* ───────────── Keyboard shortcut help (?) ──────────────── */
  function showHelpModal() {
    var existing = document.querySelector(".kbd-modal-backdrop");
    if (existing) { existing.remove(); return; }
    var m = document.createElement("div");
    m.className = "kbd-modal-backdrop";
    m.innerHTML =
      '<div class="kbd-modal" role="dialog" aria-label="Keyboard shortcuts">' +
      '  <h3>Keyboard shortcuts</h3>' +
      '  <table><tbody>' +
      '    <tr><td>Command palette</td><td><span class="kbd">⌘</span> <span class="kbd">K</span> · <span class="kbd">Ctrl</span> <span class="kbd">K</span></td></tr>' +
      '    <tr><td>Search</td><td><span class="kbd">/</span></td></tr>' +
      '    <tr><td>This help</td><td><span class="kbd">?</span></td></tr>' +
      '    <tr><td>Theme cycle</td><td><span class="kbd">⌘</span> <span class="kbd">⇧</span> <span class="kbd">D</span></td></tr>' +
      '    <tr><td>Home</td><td><span class="kbd">g</span> <span class="kbd">h</span></td></tr>' +
      '    <tr><td>Practice</td><td><span class="kbd">g</span> <span class="kbd">p</span></td></tr>' +
      '    <tr><td>Try it</td><td><span class="kbd">g</span> <span class="kbd">t</span></td></tr>' +
      '    <tr><td>Learn studio</td><td><span class="kbd">g</span> <span class="kbd">l</span></td></tr>' +
      '    <tr><td>Tools (mechanics)</td><td><span class="kbd">g</span> <span class="kbd">o</span></td></tr>' +
      '    <tr><td>Glossary</td><td><span class="kbd">g</span> <span class="kbd">g</span></td></tr>' +
      '    <tr><td>Conjugation drill</td><td><span class="kbd">g</span> <span class="kbd">c</span></td></tr>' +
      '    <tr><td>Close any overlay</td><td><span class="kbd">esc</span></td></tr>' +
      '  </tbody></table>' +
      '  <button class="kbd-modal-close" type="button">Close</button>' +
      '</div>';
    document.body.appendChild(m);
    m.addEventListener("click", function (e) { if (e.target === m) m.remove(); });
    m.querySelector(".kbd-modal-close").addEventListener("click", function () { m.remove(); });
  }

  /* ───────────── Global hotkeys ───────────────────────────── */
  var lastG = 0;
  document.addEventListener("keydown", function (e) {
    var inField = e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable);
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (palette) closePalette(); else openPalette();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === "d") {
      e.preventDefault();
      themeToggle && themeToggle.click();
      return;
    }
    if (inField) return;
    if (e.key === "?" && !palette) { e.preventDefault(); showHelpModal(); return; }
    if (e.key === "/" && !palette && !document.querySelector(".search-box input")) {
      e.preventDefault(); openPalette(); return;
    }
    if (e.key === "Escape") {
      if (palette) closePalette();
      var hm = document.querySelector(".kbd-modal-backdrop");
      if (hm) hm.remove();
      return;
    }
    // g-prefix shortcuts: gh, gp, gt, gl, gg (glossary), etc.
    // Check pending prefix BEFORE setting a new one so g+g works.
    if (lastG && (Date.now() - lastG) < 1100) {
      var targets = { h: "/", p: "/practice/", t: "/try/", l: "/learn/", a: "/adrs/", s: "/search/", o: "/tools/", g: "/glossary/", c: "/practice/#conjugation" };
      var t = targets[e.key.toLowerCase()];
      if (t) { e.preventDefault(); window.location.href = pathJoin(t); lastG = 0; return; }
      lastG = 0;
    }
    if (e.key === "g") { lastG = Date.now(); return; }
  });

  /* ───────────── Landing quick-quiz ("What's my level?") ──── */
  // 4 FEI-shape items spanning A2 → C1. Heuristic scoring (count correct
  // weighted by difficulty) → suggested NCLC band + onward link.
  (function () {
    var stage = document.getElementById("qq-stage");
    if (!stage) return;
    var QQ = [
      { lvl: "A2", q: "Choisis la phrase correcte.", o: [
          "Je suis allé au marché hier.", "Je suis aller au marché hier.",
          "Je vais allé au marché hier.", "J'ai aller au marché hier."
        ], c: 0 },
      { lvl: "B1", q: "« Bien que la mesure ___ utile, son application reste difficile. »", o: [
          "est", "soit", "était", "serait"
        ], c: 1 },
      { lvl: "B2", q: "Synonyme le plus précis de « contraindre » dans : « la pluie nous a contraints à reporter ».", o: [
          "encouragés", "obligés", "invités", "autorisés"
        ], c: 1 },
      { lvl: "C1", q: "« Il n'en demeure pas moins que… » introduit…", o: [
          "une question rhétorique", "une concession suivie d'une affirmation forte",
          "un exemple chiffré", "une définition technique"
        ], c: 1 }
    ];
    var levelMap = ["A2 — NCLC 4", "B1 — NCLC 5–6", "B2 — NCLC 7–8", "C1 — NCLC 9–10"];
    var state = { i: 0, hits: [false, false, false, false] };

    function render() {
      var p1 = document.getElementById("qq-p1"), p2 = document.getElementById("qq-p2"),
          p3 = document.getElementById("qq-p3"), p4 = document.getElementById("qq-p4");
      [p1, p2, p3, p4].forEach(function (el, idx) { if (el) el.classList.toggle("is-done", idx < state.i); });
      var iEl = document.getElementById("qq-i");
      var nEl = document.getElementById("qq-n");
      if (iEl) iEl.textContent = Math.min(state.i + 1, QQ.length);
      if (nEl) nEl.textContent = QQ.length;

      if (state.i >= QQ.length) {
        var hits = state.hits;
        // Highest-difficulty correct answer → band; need consecutive correctness from A2 up to that level.
        var band = -1;
        for (var k = 0; k < hits.length; k++) {
          if (hits[k]) band = k; else break;
        }
        if (band < 0) {
          // None right → band stays -1
        }
        var label = band < 0 ? "Below A2 — start from foundations" : levelMap[band];
        var path = band >= 2
          ? '<a class="btn btn-primary" href="' + pathJoin('/practice/') + '#diagnostic">Take the 8-item placement</a><a class="btn btn-secondary" href="' + pathJoin('/learn/') + '">Open learner studio</a>'
          : band >= 0
            ? '<a class="btn btn-primary" href="' + pathJoin('/practice/') + '">Start daily practice</a><a class="btn btn-secondary" href="' + pathJoin('/tools/') + '">Brush up mechanics</a>'
            : '<a class="btn btn-primary" href="' + pathJoin('/LEARNER_GUIDE/') + '">Read the 12-week guide</a><a class="btn btn-secondary" href="' + pathJoin('/tools/') + '">Open the toolkit</a>';
        stage.innerHTML =
          '<div class="quickquiz-result">' +
          '  <span class="level-badge">' + label + '</span>' +
          '  <h4>You answered ' + hits.filter(Boolean).length + ' / ' + QQ.length + ' correctly.</h4>' +
          '  <p>This is a 90-second vibe-check, not a calibrated diagnostic. The 8-item placement on /practice/ gives a per-skill NCLC point estimate with a credible interval. <strong>If the vibe-check says NCLC 7–8 but the calibrated one says NCLC 5, trust the latter.</strong></p>' +
          '  <div class="quickquiz-actions">' + path + '</div>' +
          '  <button class="quickquiz-restart" type="button">↻ Try again</button>' +
          '</div>';
        var restart = stage.querySelector(".quickquiz-restart");
        if (restart) restart.addEventListener("click", function () { state = { i: 0, hits: [false, false, false, false] }; render(); });
        return;
      }

      var item = QQ[state.i];
      var letters = ["A", "B", "C", "D"];
      var optsHtml = item.o.map(function (o, idx) {
        return '<button class="quickquiz-opt" data-idx="' + idx + '" type="button">' +
          '<span class="quickquiz-opt-letter">' + letters[idx] + '</span>' +
          '<span lang="fr">' + o + '</span></button>';
      }).join("");
      stage.innerHTML =
        '<p class="quickquiz-q" lang="fr">' + item.q + '</p>' +
        '<div class="quickquiz-opts">' + optsHtml + '</div>';
      stage.querySelectorAll(".quickquiz-opt").forEach(function (b) {
        b.addEventListener("click", function () {
          var idx = parseInt(b.dataset.idx, 10);
          state.hits[state.i] = (idx === item.c);
          state.i++;
          render();
        });
      });
    }
    render();
  })();

  /* ───────────── Offline indicator ─────────────────────────── */
  // Show a small chip when the browser reports the user has gone offline; hide
  // when they come back. Cheap nudge that the PWA's cached content is still
  // usable. Reduced-motion still gets the chip, just without slide animation.
  (function () {
    var chip = null;
    function show() {
      if (chip) return;
      chip = document.createElement("div");
      chip.className = "offline-chip";
      chip.setAttribute("role", "status");
      chip.innerHTML = '<span class="offline-dot" aria-hidden="true"></span> Offline · cached pages and drills still work';
      document.body.appendChild(chip);
      requestAnimationFrame(function () { chip.classList.add("is-visible"); });
    }
    function hide() {
      if (!chip) return;
      chip.classList.remove("is-visible");
      var c = chip; chip = null;
      setTimeout(function () { c.remove(); }, 320);
    }
    window.addEventListener("offline", show);
    window.addEventListener("online", hide);
    if (typeof navigator.onLine === "boolean" && !navigator.onLine) show();
  })();

  /* ───────────── PWA service-worker registration ──────────── */
  if ("serviceWorker" in navigator && window.location.protocol !== "file:") {
    window.addEventListener("load", function () {
      var swUrl = pathJoin("/sw.js");
      var scope = (window.SITE_BASE || "") + "/";
      navigator.serviceWorker.register(swUrl, { scope: scope })
        .then(function (reg) {
          // If an update is found, prompt it to activate.
          if (!reg) return;
          reg.addEventListener("updatefound", function () {
            var nw = reg.installing;
            if (!nw) return;
            nw.addEventListener("statechange", function () {
              if (nw.state === "installed" && navigator.serviceWorker.controller) {
                // A fresh SW is ready; tell it to take over on next load.
                try { nw.postMessage({ type: "SKIP_WAITING" }); } catch (e) {}
              }
            });
          });
        })
        .catch(function () { /* SW optional */ });
    });
  }
})();
