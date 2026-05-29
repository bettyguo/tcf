/*
 * tcf-accel — Client-side search.
 * Loads the pre-built /search-index.json (one entry per published page) and
 * scores results with TF-IDF + title boost + phrase boost. Snippets are
 * extracted around the strongest match.
 *
 * No backend, no fetch outside our own origin, no tracking.
 */
(function () {
  "use strict";

  var INDEX_URL = (window.SITE_BASE || "") + "/search-index.json";
  var STOPWORDS = new Set("the a an and or to of in for on with by at as is be are this that these those it its from".split(" "));

  var index = null;
  var df = null; // document frequency per term
  var qInput = document.getElementById("search-q");
  var results = document.getElementById("search-results");
  var status = document.getElementById("search-status");
  var countEl = document.getElementById("search-count");
  if (!qInput || !results) return;

  function tokenize(s) {
    return (s || "").toLowerCase()
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter(function (t) { return t && t.length > 1 && !STOPWORDS.has(t); });
  }

  function loadIndex() {
    return fetch(INDEX_URL, { cache: "force-cache" }).then(function (r) { return r.json(); }).then(function (raw) {
      index = raw.map(function (e) {
        var tokens = tokenize(e.title + " " + (e.excerpt || "") + " " + (e.body || ""));
        var tf = {};
        tokens.forEach(function (t) { tf[t] = (tf[t] || 0) + 1; });
        return { title: e.title, url: e.url, excerpt: e.excerpt, body: e.body, tf: tf, len: tokens.length };
      });
      df = {};
      index.forEach(function (doc) {
        Object.keys(doc.tf).forEach(function (t) { df[t] = (df[t] || 0) + 1; });
      });
      return index;
    });
  }

  function score(doc, qTokens, qPhrase) {
    var s = 0;
    var N = index.length;
    qTokens.forEach(function (t) {
      var tf = doc.tf[t] || 0;
      if (tf === 0) return;
      var idf = Math.log(1 + N / (df[t] || 1));
      s += (tf / Math.sqrt(doc.len || 1)) * idf;
    });
    if (qPhrase && doc.body && doc.body.toLowerCase().indexOf(qPhrase) >= 0) s += 5;
    if (qPhrase && doc.title && doc.title.toLowerCase().indexOf(qPhrase) >= 0) s += 10;
    qTokens.forEach(function (t) {
      if (doc.title && doc.title.toLowerCase().indexOf(t) >= 0) s += 3;
    });
    return s;
  }

  function highlight(text, terms) {
    if (!text) return "";
    var safe = text.replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; });
    terms.forEach(function (t) {
      var re = new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      safe = safe.replace(re, "<mark>$1</mark>");
    });
    return safe;
  }

  function snippet(body, qTokens, qPhrase) {
    if (!body) return "";
    var low = body.toLowerCase();
    var pos = qPhrase ? low.indexOf(qPhrase) : -1;
    if (pos < 0) {
      for (var i = 0; i < qTokens.length; i++) {
        var p = low.indexOf(qTokens[i]);
        if (p >= 0) { pos = p; break; }
      }
    }
    if (pos < 0) return body.slice(0, 180) + (body.length > 180 ? "…" : "");
    var start = Math.max(0, pos - 90);
    var end = Math.min(body.length, pos + 130);
    var pre = start > 0 ? "… " : "";
    var post = end < body.length ? " …" : "";
    return pre + body.slice(start, end) + post;
  }

  function render(q) {
    if (!index) { status.textContent = "Loading index…"; return; }
    if (!q) {
      results.innerHTML = "";
      countEl.textContent = "0";
      status.innerHTML = "Type to search · <strong>0</strong> results";
      return;
    }
    var tokens = tokenize(q);
    var phrase = q.toLowerCase().trim();
    if (!tokens.length) {
      results.innerHTML = '<p class="cmdk-empty">Try a different query.</p>';
      countEl.textContent = "0";
      return;
    }
    var scored = index.map(function (d) { return { d: d, s: score(d, tokens, phrase) }; }).filter(function (x) { return x.s > 0; });
    scored.sort(function (a, b) { return b.s - a.s; });
    var top = scored.slice(0, 30);
    countEl.textContent = scored.length;
    status.innerHTML = "Showing " + Math.min(top.length, 30) + " of <strong>" + scored.length + "</strong> matches for <em>" + q.replace(/[<>&]/g, "") + "</em>";
    if (!top.length) {
      results.innerHTML = '<p class="cmdk-empty">No matches. Try a broader term — e.g. <code>readiness</code>, <code>NCLC</code>, <code>kappa</code>, <code>posterior</code>.</p>';
      return;
    }
    var html = top.map(function (x) {
      var d = x.d;
      var s = snippet(d.body || d.excerpt, tokens, phrase);
      return '<article class="search-result">' +
        '<h3 class="search-result-title"><a href="' + d.url + '">' + highlight(d.title, tokens.concat([phrase])) + '</a></h3>' +
        '<p class="search-result-url">' + d.url + '</p>' +
        '<p class="search-result-excerpt">' + highlight(s, tokens.concat([phrase])) + '</p>' +
        '</article>';
    }).join("");
    results.innerHTML = html;
  }

  var renderTimer = null;
  function rerender() {
    clearTimeout(renderTimer);
    renderTimer = setTimeout(function () { render(qInput.value.trim()); }, 80);
  }
  qInput.addEventListener("input", rerender);
  qInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      // Jump to first result on Enter.
      var first = results.querySelector(".search-result a");
      if (first) window.location.href = first.getAttribute("href");
    }
  });

  // Allow deep-linking: /search/?q=foo
  try {
    var p = new URLSearchParams(window.location.search);
    if (p.get("q")) { qInput.value = p.get("q"); }
  } catch (e) {}

  status.textContent = "Loading search index…";
  loadIndex().then(function () {
    status.innerHTML = index.length + " pages indexed · type to search";
    if (qInput.value) render(qInput.value.trim());
  }).catch(function (e) {
    status.textContent = "Could not load search index.";
    console.error(e);
  });

  // / focuses the search box from anywhere on the search page.
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement !== qInput && !(e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) {
      e.preventDefault();
      qInput.focus();
      qInput.select();
    }
  });
})();
