self.addEventListener('install', function(event) {
    console.log('Sedef PWA Servisi Kuruldu.');
});

self.addEventListener('fetch', function(event) {
    // Canlı borsa olduğu için önbellek (cache) yapmıyoruz, veriyi hep anlık çekiyoruz.
    event.respondWith(fetch(event.request));
});