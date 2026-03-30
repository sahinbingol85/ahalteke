self.addEventListener('install', (event) => {
    console.log('Ahal Teke Rezervasyon PWA Motoru Kuruldu!');
    self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
    // Sitenin normal şekilde canlı çalışmasına izin verir (Önbellekten eski veri göstermez)
    event.respondWith(fetch(event.request));
});self.addEventListener('install', (event) => {
    console.log('Ahal Teke Rezervasyon PWA Motoru Kuruldu!');
    self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
    // Sitenin normal şekilde canlı çalışmasına izin verir (Önbellekten eski veri göstermez)
    event.respondWith(fetch(event.request));
});
