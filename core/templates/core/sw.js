const CACHE_NAME = 'ahalteke-v3'; // v3 yaptık ki cihazlar eski bozuk versiyonu hemen unutup bunu kursun

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

// İnternet isteklerini dinleme
self.addEventListener('fetch', (e) => {
    
    // EKLENEN HAYAT KURTARICI KOD: 
    // Sadece GET (sayfa yükleme) isteklerine karış. 
    // POST (Form gönderme, Giriş yapma) isteklerini direkt Django'ya bırak!
    if (e.request.method !== 'GET') {
        return; 
    }

    e.respondWith(
        fetch(e.request).catch(() => {
            return caches.match(e.request);
        })
    );
});