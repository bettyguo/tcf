---
layout: null
sitemap: false
permalink: /sw.js
---
/* tcf-accel service worker.
 *
 * Strategy:
 *   - HTML/navigation: network-first with cache fallback, then offline shell.
 *   - CSS/JS/fonts/images: stale-while-revalidate.
 *   - JSON (search index, audit data): stale-while-revalidate.
 *   - Cap each cache bucket. Skip cross-origin / non-GET / Web Speech.
 *   - Per-URL precache adds (cache.addAll is atomic; one 404 kills it).
 */
const VERSION = "tcf-1.0.5";
const CORE = "tcf-core-" + VERSION;
const ASSETS = "tcf-assets-" + VERSION;
const PAGES = "tcf-pages-" + VERSION;

const ROOT = "{{ '/' | relative_url }}";
const OFFLINE_SHELL = ROOT; // landing page renders without JS; safe fallback.

const CORE_URLS = [
  ROOT,
  "{{ '/practice/' | relative_url }}",
  "{{ '/learn/' | relative_url }}",
  "{{ '/tools/' | relative_url }}",
  "{{ '/glossary/' | relative_url }}",
  "{{ '/try/' | relative_url }}",
  "{{ '/search/' | relative_url }}",
  "{{ '/LIMITATIONS/' | relative_url }}",
  "{{ '/assets/css/style.css' | relative_url }}",
  "{{ '/assets/js/site.js' | relative_url }}",
  "{{ '/assets/js/phrase.js' | relative_url }}",
  "{{ '/assets/js/demo.js' | relative_url }}",
  "{{ '/assets/js/learn.js' | relative_url }}",
  "{{ '/assets/js/practice.js' | relative_url }}",
  "{{ '/assets/js/extra-drills.js' | relative_url }}",
  "{{ '/assets/js/tools.js' | relative_url }}",
  "{{ '/assets/js/converter.js' | relative_url }}",
  "{{ '/assets/js/search.js' | relative_url }}",
  "{{ '/assets/img/favicon.svg' | relative_url }}",
  "{{ '/manifest.webmanifest' | relative_url }}",
  "{{ '/search-index.json' | relative_url }}"
];

async function precache() {
  const cache = await caches.open(CORE);
  // Add per-URL so a single 404 doesn't abort the whole precache.
  await Promise.allSettled(CORE_URLS.map((u) => cache.add(new Request(u, { cache: "reload" }))));
}

self.addEventListener("install", (event) => {
  event.waitUntil(precache());
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k.startsWith("tcf-") && k.indexOf(VERSION) < 0).map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

async function capCache(name, max) {
  const cache = await caches.open(name);
  const keys = await cache.keys();
  if (keys.length > max) {
    await Promise.all(keys.slice(0, keys.length - max).map((req) => cache.delete(req)));
  }
}

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // HTML/navigation: network-first → cached page → offline shell.
  const accept = req.headers.get("accept") || "";
  if (accept.includes("text/html") || req.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const resp = await fetch(req);
        if (resp && resp.ok) {
          const copy = resp.clone();
          caches.open(PAGES).then((c) => { c.put(req, copy); capCache(PAGES, 40); });
        }
        return resp;
      } catch (e) {
        const cached = await caches.match(req);
        if (cached) return cached;
        const shell = await caches.match(OFFLINE_SHELL);
        return shell || new Response("Offline — open /practice/, /learn/, or /tools/ from your home screen to use cached drills.", {
          status: 503, statusText: "Offline", headers: { "Content-Type": "text/plain; charset=utf-8" }
        });
      }
    })());
    return;
  }

  // Assets + JSON: stale-while-revalidate.
  event.respondWith(
    caches.match(req).then((cached) => {
      const fetchPromise = fetch(req).then((resp) => {
        if (resp && resp.ok) {
          const copy = resp.clone();
          const bucket = url.pathname.endsWith(".json") ? PAGES : ASSETS;
          caches.open(bucket).then((c) => { c.put(req, copy); capCache(bucket, 80); });
        }
        return resp;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
