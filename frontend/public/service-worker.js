/* ============================================================
   CarDetailing AI — Service Worker
   ============================================================ */

const CACHE_NAME = 'cardetailing-v1';
const STATIC_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
];

// Install — cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_URLS)),
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

// Fetch — network first, fallback to cache, then offline page
self.addEventListener('fetch', (event) => {
  // API requests — network only
  if (event.request.url.includes('/api/') || event.request.url.includes('/uploads/')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const cacheResponse = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cacheResponse));
        return response;
      })
      .catch(() => caches.match(event.request).then((cached) => {
        return cached || caches.match('/offline.html');
      })),
  );
});
