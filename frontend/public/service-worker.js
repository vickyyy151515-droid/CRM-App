// CRM Hub Service Worker
// IMPORTANT: Update version to force cache refresh on deploy
const CACHE_NAME = 'crm-hub-v4-deploy-fix';
const OFFLINE_URL = '/offline.html';

// Only cache non-hashed assets
const PRECACHE_ASSETS = [
  '/offline.html',
  '/manifest.json'
];

// Install event - cache essential assets only
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Precaching essential assets');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up ALL old caches immediately
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => cacheName !== CACHE_NAME)
          .map((cacheName) => {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - network first strategy
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/api/')) return;
  if (!event.request.url.startsWith('http')) return;

  // NEVER cache JS/CSS bundles - they have cache-busting hashes already
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/static/')) {
    // Let the browser handle static assets normally (no SW interference)
    return;
  }

  // For navigation requests (HTML pages) - always network first, no caching
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .catch(() => caches.match(OFFLINE_URL) || new Response('Offline', { status: 503 }))
    );
    return;
  }

  // For other assets - network first, fallback to cache
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.status === 200 && !url.pathname.startsWith('/static/')) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request)
          .then((cachedResponse) => {
            if (cachedResponse) return cachedResponse;
            return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
          });
      })
  );
});

// Handle messages from the client
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});
