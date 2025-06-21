// app/static/js/service-worker.js

// Listener for the 'install' event.
// This is a good place to cache static assets if needed, but for push notifications primarily,
// it's often kept simple.
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  // event.waitUntil(
  //   caches.open('your-cache-name').then((cache) => {
  //     return cache.addAll([
  //       '/',
  //       '/static/css/main.css',
  //       '/static/js/main.js',
  //       // Add other assets you want to cache
  //     ]);
  //   })
  // );
  // Force the waiting service worker to become the active service worker.
  self.skipWaiting();
});

// Listener for the 'activate' event.
// This is a good place to clean up old caches.
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating...');
  // event.waitUntil(
  //   caches.keys().then((cacheNames) => {
  //     return Promise.all(
  //       cacheNames.map((cacheName) => {
  //         if (cacheName !== 'your-cache-name') { // Replace with your cache name
  //           return caches.delete(cacheName);
  //         }
  //       })
  //     );
  //   })
  // );
  // Tell the active service worker to take control of the page immediately.
  return self.clients.claim();
});

// Listener for 'push' events.
// This is triggered when a push message is received from the server.
self.addEventListener('push', (event) => {
  console.log('Service Worker: Push event received.');

  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      console.error('Service Worker: Error parsing push data json', e);
      data = {
        title: 'Push Notification',
        body: event.data.text() || 'You have a new message.',
      };
    }
  } else {
    data = {
      title: 'Push Notification',
      body: 'You have a new message.',
    };
  }

  const title = data.title || 'Equipment Maintenance Reminder';
  const options = {
    body: data.body || 'You have an update regarding equipment maintenance.',
    // icon: data.icon || '/static/img/logo-192x192.png', // Default icon removed as file doesn't exist
    // badge: data.badge || '/static/img/badge-72x72.png', // Default badge removed as file doesn't exist
    // tag: 'maintenance-notification', // Optional: Coalesces notifications with the same tag
    // renotify: true, // Optional: Vibrate/sound even if a notification with the same tag exists
    data: {
      url: data.url || '/', // URL to open on click, defaults to home
      // You can add more custom data here
    },
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Listener for 'notificationclick' event.
// This is triggered when a user clicks on a displayed notification.
self.addEventListener('notificationclick', (event) => {
  console.log('Service Worker: Notification clicked.');
  event.notification.close(); // Close the notification

  // Open the URL specified in the notification's data, or the root page.
  const urlToOpen = event.notification.data.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // If a window for this app is already open, focus it.
      for (const client of clientList) {
        // Note: client.url might have a trailing slash, ensure comparison is robust
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      // Otherwise, open a new window.
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
