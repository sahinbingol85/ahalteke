self.addEventListener('install', (event) => {
    console.log('Ahal Teke Hakem Uygulaması Kuruldu!');
    self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
    // Sitenin normal şekilde çalışmasına izin verir
    event.respondWith(fetch(event.request));
});