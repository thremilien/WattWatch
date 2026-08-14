// Exists only to satisfy home-screen "installability" checks. No caching:
// this dashboard shows live device data, so a stale cache would be worse
// than no offline support at all.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', (event) => event.respondWith(fetch(event.request)));
