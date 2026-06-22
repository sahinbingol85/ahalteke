const CACHE_NAME = 'ahalteke-v5'; // Versiyonu v5 yaptık ki cihazlar hemen güncellensin

// Başlangıçta hafızaya alınacak temel yollar
const urlsToCache = [
    '/yonetim_paneli/hakem/',
    '/yonetim_paneli/fikstur-yonetimi/',
    '/rezervasyon/'
];

// 1. Kurulum Aşaması
self.addEventListener('install', (e) => {
    console.log('[Service Worker] Kuruldu (v5)');
    e.waitUntil(
        caches.open(CACHE_NAME)
        .then((cache) => {
            console.log('[Service Worker] Temel dosyalar önbelleğe alınıyor');
            return cache.addAll(urlsToCache).catch(err => console.log('Önbellek hatası (Önemli değil):', err));
        })
    );
    self.skipWaiting();
});

// 2. Aktivasyon Aşaması (Eski versiyonları temizler)
self.addEventListener('activate', (e) => {
    console.log('[Service Worker] Aktif Edildi');
    e.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    console.log('[Service Worker] Eski önbellek siliniyor:', key);
                    return caches.delete(key);
                }
            }));
        })
    );
    return self.clients.claim();
});

// 3. İnternet İsteklerini Dinleme (Network-First Stratejisi)
self.addEventListener('fetch', (e) => {
    
    // Sadece GET (sayfa yükleme) isteklerine karış. 
    // POST (Form gönderme, skor kaydetme) isteklerini direkt Django'ya bırak!
    if (e.request.method !== 'GET') {
        return; 
    }

    e.respondWith(
        fetch(e.request)
        .then(response => {
            // Eğer internet varsa, sayfayı getirirken bir kopyasını da sessizce güncel hafızaya kaydet
            const resClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
                cache.put(e.request, resClone);
            });
            return response;
        })
        .catch(() => {
            // İNTERNET YOKSA (Çevrimdışı): Sayfayı önbellekten getir
            console.log('[Service Worker] Ağ hatası, önbellekten getiriliyor:', e.request.url);
            return caches.match(e.request);
        })
    );
});