const CACHE_NAME = 'ahalteke-v2';

// Kurulum Aşaması
self.addEventListener('install', (e) => {
    console.log('[Service Worker] Kuruldu');
    self.skipWaiting();
});

// Aktivasyon Aşaması
self.addEventListener('activate', (e) => {
    console.log('[Service Worker] Aktif Edildi');
    return self.clients.claim();
});

// İnternet kesilirse diye basit bir dinleyici (Uygulamanın yüklenmesini tetikler)
self.addEventListener('fetch', (e) => {
    e.respondWith(
        fetch(e.request).catch(() => {
            return caches.match(e.request);
        })
    );
});