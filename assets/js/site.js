// tcf-accel docs site
// Vanilla JS: nav toggle, theme cycle (auto → light → dark → auto).

(function () {
  // Mobile nav toggle.
  var toggle = document.querySelector(".nav-toggle");
  var menu = document.getElementById("nav-menu");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    // Close menu when a link is clicked (so SPA-style navigation feels right).
    menu.addEventListener("click", function (e) {
      if (e.target.closest("a")) {
        menu.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Theme cycle: auto → light → dark → auto.
  var themeToggle = document.querySelector(".theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme") || "auto";
      var next = current === "auto" ? "light" : current === "light" ? "dark" : "auto";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("tcf-theme", next); } catch (e) {}
      themeToggle.setAttribute("title", "Theme: " + next);
    });
  }
})();
