/* CarDetailing AI — PWA service worker: оболочка + офлайн записей. */

const CACHE_NAME = 'cardetailing-pwa-v2';
const SHELL = [
  '/offline.html',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/images/logo-formula-sport.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL).catch(() => undefined)),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

function isAppointmentsMe(url) {
  try {
    const u = new URL(url);
    return u.pathname === '/api/appointments/me' || u.pathname.endsWith('/api/appointments/me');
  } catch {
    return false;
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = req.url;
  if (url.includes('/uploads/')) return;
  if (url.includes('@vite') || url.includes('/src/') || url.includes('node_modules')) return;

  if (isAppointmentsMe(url)) {
    event.respondWith(
      fetch(req)
        .then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return response;
        })
        .catch(() => caches.match(req).then((cached) => cached || Response.error())),
    );
    return;
  }

  if (url.includes('/api/')) return;

  event.respondWith(
    fetch(req)
      .then((response) => {
        if (response && response.ok && req.url.startsWith(self.location.origin)) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
        }
        return response;
      })
      .catch(() =>
        caches.match(req).then((cached) => cached || caches.match('/offline.html')),
      ),
  );
});
