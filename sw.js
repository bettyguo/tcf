---
layout: null
sitemap: false
permalink: /sw.js
---
/* tcf-accel service worker.
 * Strategy:
 *   - HTML: network-first with cache fallback (so updates ship immediately).
 *   - CSS/JS/fonts/images: stale-while-revalidate.
 *   - JSON (search index, audit data): stale-while-revalidate.
 *   - Cap cache size to 80 entries.
 *   - Skip Web Speech API / cross-origin / non-GET.
 */
const VERSION = "tcf-1.0.3";
const CORE = "tcf-core-" + VERSION;
const ASSETS = "tcf-assets-" + VERSION;
const PAGES = "tcf-pages-" + VERSION;

const CORE_URLS = [
  "{{ '/' | relative_url }}",
  "{{ '/practice/' | relative_url }}",
  "{{ '/learn/' | relative_url }}",
  "{{ '/tools/' | relative_url }}",
  "{{ '/glossary/' | relative_url }}",
  "{{ '/try/' | relative_url }}",
  "{{ '/search/' | relative_url }}",
  "{{ '/LIMITATIONS/' | relative_url }}",
  "{{ '/assets/css/style.css' | relative_url }}",
  "{{ '/assets/js/site.js' | relative_url }}",
  "{{ '/assets/js/demo.js' | relative_url }}",
  "{{ '/assets/js/learn.js' | relative_url }}",
  "{{ '/assets/js/practice.js' | relative_url }}",
  "{{ '/assets/js/tools.js' | relative_url }}",
  "{{ '/assets/js/search.js' | relative_url }}",
  "{{ '/assets/img/favicon.svg' | relative_url }}",
  "{{ '/manifest.webmanifest' | relative_url }}"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CORE).then((cache) => cache.addAll(CORE_URLS).catch(() => {}))
  );
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

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // HTML: network-first.
  const accept = req.headers.get("accept") || "";
  if (accept.includes("text/html") || req.mode === "navigate") {
    event.respondWith(
      fetch(req).then((resp) => {
        const copy = resp.clone();
        caches.open(PAGES).then((c) => { c.put(req, copy); capCache(PAGES, 40); });
        return resp;
      }).catch(() => caches.match(req).then((c) => c || caches.match("{{ '/' | relative_url }}")))
    );
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
