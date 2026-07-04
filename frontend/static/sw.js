// v2: cache-first on page navigations meant every HTML page (dashboard,
// recipes, settings...) got frozen at whatever it looked like the first time
// it was ever loaded, and never refetched from the network again - so things
// like swapping a recipe's day, deleting a recipe, or any other server-side
// change would silently never show up on pages the browser had already
// cached, forever, until the cache was manually cleared. Bumping the cache
// name here forces every existing install to drop its old (permanently
// stale) cache on next activate.
const CACHE_NAME = "pi-menu-ukesmeny-v2";
const STATIC_ASSETS = ["/static/style.css", "/static/manifest.json"];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const { request } = event;
    if (request.method !== "GET") return;

    const url = new URL(request.url);

    // Never cache API calls - always hit the network live.
    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/login") || url.pathname.startsWith("/callback")) {
        event.respondWith(fetch(request));
        return;
    }

    // Page navigations (the dashboard, recipe pages, settings, etc.) always
    // reflect server state - network-first, only falling back to whatever's
    // cached if the network is genuinely unreachable (offline support).
    if (request.mode === "navigate" || (request.headers.get("accept") || "").includes("text/html")) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
                    return response;
                })
                .catch(() => caches.match(request).then((cached) => cached || caches.match("/")))
        );
        return;
    }

    // Cache-first for genuinely static assets (CSS/JS/images/fonts).
    event.respondWith(
        caches.match(request).then((cached) => {
            if (cached) return cached;
            return fetch(request).then((response) => {
                if (!response || response.status !== 200 || response.type === "opaque") return response;
                const clone = response.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
                return response;
            });
        })
    );
});
