// Служебный скрипт приложения «Мой универ»: хранит копию страницы, чтобы она открывалась без интернета.
// Твои данные (расписание, задания, оценки) лежат в самом браузере и от этого скрипта не зависят.
const VERSION = 'muni-v1';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const mine = url.origin === self.location.origin;
  const fonts = url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';
  if (!mine && !fonts) return;                      // Google Диск, вход Google и всё чужое идёт напрямую, без кеша
  e.respondWith(fresh(e));
});

// Сначала отдаём то, что есть в кеше (быстро и без сети), а свежую версию тихо подтягиваем для следующего раза
async function fresh(e){
  const req = e.request, cache = await caches.open(VERSION);
  const cached = await cache.match(req);
  const net = fetch(req).then(res => {
    if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone());
    return res;
  }).catch(() => null);
  if (cached){ e.waitUntil(net); return cached; }
  const res = await net;
  if (res) return res;
  if (req.mode === 'navigate') return (await cache.match('index.html')) || (await cache.match('./')) || Response.error();
  return Response.error();
}
