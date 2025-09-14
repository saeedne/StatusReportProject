// static/sw.js
const CACHE_NAME = 'contract-manager-v1';
const urlsToCache = [
    '/',
    '/record_form',
    '/contract_form',
    '/static/css/style.css',
    '/static/icons/icon.svg'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => {
            console.log('Opened cache');
            return cache.addAll(urlsToCache);
        })
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
        .then(response => {
            if (response) {
                return response;
            }
            return fetch(event.request);
        })
    );
});
