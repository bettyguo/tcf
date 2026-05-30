/* tcf-accel — Achievements / milestones
 *
 * Quiet wins. No notification spam — toast appears once per achievement
 * unlock, and a badge ribbon shows on /practice/#stats (and on the
 * landing's footer area if the host is present).
 *
 * Storage namespace: tcf.practice.achievements (array of unlocked IDs).
 * Exposes window.tcfCheckAchievements() so drills can trigger a check
 * after a meaningful state change.
 */
(function () {
  "use strict";

  var LS = "tcf.practice.";
  function lsGet(k, fb) {
    try { var v = localStorage.getItem(LS + k); return v == null ? fb : JSON.parse(v); }
    catch (e) { return fb; }
  }
  function lsSet(k, v) {
    try { localStorage.setItem(LS + k, JSON.stringify(v)); } catch (e) {}
  }

  // Each achievement: { id, title, desc, icon, test(stats) -> bool }
  var ACHIEVEMENTS = [
    {
      id: "first_session",
      title: "First session",
      desc: "You showed up. That's the hardest part.",
      icon: "🎯",
      test: function (s) { return s.sessions >= 1; }
    },
    {
      id: "streak_3",
      title: "3-day streak",
      desc: "Three days in a row — the habit is starting to bite.",
      icon: "🔥",
      test: function (s) { return s.streak >= 3; }
    },
    {
      id: "streak_7",
      title: "7-day streak",
      desc: "A full week. Past this point, momentum does some of the work.",
      icon: "🔥🔥",
      test: function (s) { return s.streak >= 7; }
    },
    {
      id: "streak_30",
      title: "30-day streak",
      desc: "A month. You're not 'studying for TCF' anymore — you're a French learner.",
      icon: "🏔",
      test: function (s) { return s.streak >= 30; }
    },
    {
      id: "vocab_50",
      title: "50 vocab cards learned",
      desc: "A fifth of the B1–B2 deck consolidated.",
      icon: "📚",
      test: function (s) { return s.vocabLearned >= 50; }
    },
    {
      id: "vocab_150",
      title: "150 vocab cards learned",
      desc: "Past the steepest forgetting curve. The next 100 will stick.",
      icon: "📖",
      test: function (s) { return s.vocabLearned >= 150; }
    },
    {
      id: "vocab_all",
      title: "All 241 cards learned",
      desc: "Full deck. Now teach a friend — it's the best retention multiplier.",
      icon: "🎓",
      test: function (s) { return s.vocabLearned >= 241; }
    },
    {
      id: "minutes_60",
      title: "1 hour of practice",
      desc: "Sixty minutes of actual drill time. Measurable.",
      icon: "⏱",
      test: function (s) { return s.totalMin >= 60; }
    },
    {
      id: "minutes_600",
      title: "10 hours of practice",
      desc: "The volume threshold where most learners' WPM jumps stop being noise.",
      icon: "🚀",
      test: function (s) { return s.totalMin >= 600; }
    },
    {
      id: "dictee_5",
      title: "5 dictées completed",
      desc: "Your ear is starting to chunk connected speech.",
      icon: "🎧",
      test: function (s) { return s.dictees >= 5; }
    },
    {
      id: "writing_3",
      title: "3 timed writings finished",
      desc: "The word-count fear is fading.",
      icon: "✍",
      test: function (s) { return s.writes >= 3; }
    },
    {
      id: "wpm_150",
      title: "Reading at 150+ WPM",
      desc: "T4 reading speed unlocked. CE no longer the bottleneck.",
      icon: "👀",
      test: function (s) { return s.readWpm >= 150; }
    },
    {
      id: "conjugation_50",
      title: "50 conjugations correct",
      desc: "B1 verb mastery — paradigms are getting automatic.",
      icon: "🔁",
      test: function (s) { return s.conjCorrect >= 50; }
    }
  ];

  function computeStats() {
    var hist = lsGet("history", {});
    var totalMin = Object.values(hist).reduce(function (a, b) { return a + b; }, 0);
    // Streak (mirror practice.js)
    var d = new Date(); var streak = 0;
    for (var i = 0; i < 730; i++) {
      var key = d.toISOString().slice(0, 10);
      if ((hist[key] || 0) > 0) { streak++; d.setDate(d.getDate() - 1); }
      else if (i === 0) { d.setDate(d.getDate() - 1); continue; }
      else break;
    }
    var sessions = lsGet("sessions", 0);
    // Vocab learned: count cards with ease > 2.5 and reps > 0.
    var srs = lsGet("srs", null);
    var vocabLearned = 0;
    if (srs) {
      Object.keys(srs).forEach(function (k) {
        var c = srs[k];
        if (c && c.reps > 0) vocabLearned++;
      });
    }
    // Dictées
    var dict = lsGet("dict-stats", null);
    var dictees = dict ? (dict.total || 0) : 0;
    // Writes
    var writeCount = lsGet("write-count", 0);
    // Reading WPM (median)
    var reads = lsGet("read-history", []);
    var readWpm = 0;
    if (reads && reads.length) {
      var sorted = reads.map(function (r) { return r.wpm || 0; }).sort(function (a, b) { return a - b; });
      readWpm = sorted[Math.floor(sorted.length / 2)] || 0;
    }
    // Conjugation correct
    var conj = lsGet("cd-stats", null);
    var conjCorrect = conj ? (conj.correct || 0) : 0;

    return {
      totalMin: totalMin,
      streak: streak,
      sessions: sessions,
      vocabLearned: vocabLearned,
      dictees: dictees,
      writes: writeCount,
      readWpm: readWpm,
      conjCorrect: conjCorrect
    };
  }

  function unlocked() {
    return lsGet("achievements", []);
  }

  function check() {
    var stats = computeStats();
    var have = unlocked();
    var newly = [];
    ACHIEVEMENTS.forEach(function (a) {
      if (have.indexOf(a.id) < 0 && a.test(stats)) {
        newly.push(a);
        have.push(a.id);
      }
    });
    if (newly.length) {
      lsSet("achievements", have);
      newly.forEach(function (a) { showAchievementToast(a); });
      renderBadges();
    }
  }
  window.tcfCheckAchievements = check;

  function showAchievementToast(a) {
    var t = document.createElement("div");
    t.className = "ach-toast";
    t.setAttribute("role", "status");
    t.innerHTML =
      '<div class="ach-toast-icon">' + a.icon + '</div>' +
      '<div class="ach-toast-body">' +
      '  <p class="ach-toast-eyebrow">Achievement unlocked</p>' +
      '  <p class="ach-toast-title">' + a.title + '</p>' +
      '  <p class="ach-toast-desc">' + a.desc + '</p>' +
      '</div>' +
      '<button class="ach-toast-close" type="button" aria-label="Dismiss">×</button>';
    document.body.appendChild(t);
    requestAnimationFrame(function () { t.classList.add("is-visible"); });
    var tm = setTimeout(close, 5200);
    function close() {
      clearTimeout(tm);
      t.classList.remove("is-visible");
      setTimeout(function () { t.remove(); }, 260);
    }
    t.querySelector(".ach-toast-close").addEventListener("click", close);
  }

  function renderBadges() {
    var hosts = document.querySelectorAll("[data-achievements]");
    if (!hosts.length) return;
    var have = unlocked();
    var html = '<div class="ach-grid">';
    ACHIEVEMENTS.forEach(function (a) {
      var got = have.indexOf(a.id) >= 0;
      html +=
        '<div class="ach-badge' + (got ? " is-unlocked" : "") + '" title="' + a.title + ' — ' + a.desc + '">' +
        '  <span class="ach-badge-icon">' + (got ? a.icon : "·") + '</span>' +
        '  <span class="ach-badge-title">' + a.title + '</span>' +
        '</div>';
    });
    html += '</div>';
    var got = have.length;
    var total = ACHIEVEMENTS.length;
    var prefix = '<div class="ach-head"><h4>Achievements</h4><span class="ach-count">' + got + " / " + total + '</span></div>';
    hosts.forEach(function (h) { h.innerHTML = prefix + html; });
  }

  function mount() {
    // Initial check + badge render — both safe on every page.
    check();
    renderBadges();
    // Cross-tab updates.
    window.addEventListener("storage", function (e) {
      if (!e.key || e.key.indexOf("tcf.practice.") === 0) { check(); renderBadges(); }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else { mount(); }
})();
