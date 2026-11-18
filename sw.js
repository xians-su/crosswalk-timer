/* Offline support: keeps a copy of the page, the timetable and the icons so the page opens without a network.
   Same-origin GET requests go to the network first (so updates arrive as before) and fall back to the stored copy. */
const CACHE = 'st-lucky-v1', FILES = ['./', 'index.html', 'schedule.json', 'icon.png', 'favicon.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;            // weather and camera requests are left alone
  e.respondWith(
    fetch(e.request).then(r => { if (r.ok){ const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); } return r; })
      .catch(() => caches.match(e.request, {ignoreSearch: true}).then(r => r || caches.match('index.html')))
  );
});
