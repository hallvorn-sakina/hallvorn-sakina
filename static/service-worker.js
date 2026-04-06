const CACHE_NAME = 'sakina-v1';
const SHELL = [
  '/',
  '/static/manifest.json'
];

// Install event - cache core files
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching shell assets');
        return cache.addAll(SHELL);
      })
      .catch(err => console.error('[Service Worker] Cache failed:', err))
  );
  self.skipWaiting(); // Activate immediately
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating...');
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME)
          .map(key => {
            console.log('[Service Worker] Deleting old cache:', key);
            return caches.delete(key);
          })
      );
    })
  );
  self.clients.claim(); // Take control of all clients immediately
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;
  
  // Skip external URLs (API calls, external resources)
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) {
    // For external requests, try network but don't cache
    return;
  }
  
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Clone the response before caching
        const responseToCache = response.clone();
        
        // Cache successful responses
        if (response.status === 200) {
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseToCache);
            })
            .catch(err => console.error('[Service Worker] Cache put failed:', err));
        }
        return response;
      })
      .catch(() => {
        // Network failed - try cache
        return caches.match(event.request)
          .then(cachedResponse => {
            if (cachedResponse) {
              console.log('[Service Worker] Serving from cache:', event.request.url);
              return cachedResponse;
            }
            
            // Return offline page for navigation requests
            if (event.request.mode === 'navigate') {
              return caches.match('/');
            }
            
            // Return a simple offline response for other requests
            return new Response(
              'You are offline. Please check your internet connection.',
              { status: 503, statusText: 'Service Unavailable' }
            );
          });
      })
  );
});

// Optional: Background sync for offline messages
self.addEventListener('sync', event => {
  if (event.tag === 'sync-messages') {
    event.waitUntil(syncMessages());
  }
});

async function syncMessages() {
  console.log('[Service Worker] Syncing messages...');
  // Implement your sync logic here
  // For example: send queued messages from IndexedDB
}
