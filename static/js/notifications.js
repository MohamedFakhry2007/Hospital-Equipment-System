// app/static/js/notifications.js

const VAPID_PUBLIC_KEY_URL = '/api/vapid_public_key';
const PUSH_SUBSCRIBE_URL = '/api/push_subscribe';
const PUSH_UNSUBSCRIBE_URL = '/api/push_unsubscribe';
const SERVICE_WORKER_URL = '/static/js/service-worker.js'; // Ensure this path is correct

let swRegistration = null;
let isSubscribed = false;

// Function to convert Base64 for VAPID public key
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

// Register the service worker
async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    console.error('Service Worker not supported by this browser.');
    return null;
  }
  try {
    swRegistration = await navigator.serviceWorker.register(SERVICE_WORKER_URL);
    console.log('Service Worker registered successfully:', swRegistration);
    return swRegistration;
  } catch (error) {
    console.error('Service Worker registration failed:', error);
    return null;
  }
}

// Request notification permission
async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    console.error('This browser does not support desktop notification');
    alert('This browser does not support desktop notification');
    return null;
  }

  const permission = await Notification.requestPermission();
  // Values: 'granted', 'denied', 'default'
  if (permission === 'granted') {
    console.log('Notification permission granted.');
  } else {
    console.warn('Notification permission denied or dismissed.');
  }
  return permission;
}

// Subscribe user to push notifications
async function subscribeUserToPush() {
  if (!swRegistration) {
    console.error('Service Worker not registered. Cannot subscribe.');
    return;
  }

  try {
    // Fetch VAPID public key from server
    const response = await fetch(VAPID_PUBLIC_KEY_URL);
    if (!response.ok) {
      throw new Error(`Failed to fetch VAPID public key: ${response.statusText}`);
    }
    const vapidKeyData = await response.json();
    const applicationServerKey = urlBase64ToUint8Array(vapidKeyData.publicKey);

    const subscription = await swRegistration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: applicationServerKey,
    });
    console.log('User is subscribed:', subscription);

    // Send subscription to backend
    await sendSubscriptionToBackend(subscription);
    isSubscribed = true;
    updateSubscriptionButton(); // Update UI
  } catch (error) {
    if (Notification.permission === 'denied') {
      console.warn('Permission for notifications was denied');
    } else {
      console.error('Failed to subscribe the user: ', error);
    }
    isSubscribed = false;
    updateSubscriptionButton();
  }
}

// Send subscription to backend
async function sendSubscriptionToBackend(subscription) {
  try {
    const response = await fetch(PUSH_SUBSCRIBE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(subscription),
    });
    if (!response.ok) {
      throw new Error(`Backend subscription failed: ${response.statusText}`);
    }
    console.log('Subscription sent to backend successfully.');
  } catch (error) {
    console.error('Error sending subscription to backend:', error);
    // If sending fails, we should probably unsubscribe locally to reflect the true state
    if (swRegistration && swRegistration.pushManager) {
        const currentSubscription = await swRegistration.pushManager.getSubscription();
        if (currentSubscription) {
            currentSubscription.unsubscribe().then(() => {
                console.log('Unsubscribed locally due to backend send failure.');
                isSubscribed = false;
                updateSubscriptionButton();
            });
        }
    }
  }
}

// Unsubscribe user from push notifications
async function unsubscribeUserFromPush() {
  if (!swRegistration) {
    console.error('Service Worker not registered. Cannot unsubscribe.');
    return;
  }

  try {
    const subscription = await swRegistration.pushManager.getSubscription();
    if (subscription) {
      // Send unsubscription request to backend first
      await sendUnsubscriptionToBackend(subscription);
      await subscription.unsubscribe();
      console.log('User is unsubscribed.');
      isSubscribed = false;
      updateSubscriptionButton();
    }
  } catch (error) {
    console.error('Error unsubscribing user: ', error);
    // Still update button, as local state might be out of sync or user is already unsubscribed.
    isSubscribed = false; // Assume unsubscription on error for safety
    updateSubscriptionButton();
  }
}

// Send unsubscription to backend
async function sendUnsubscriptionToBackend(subscription) {
    // We only need the endpoint for unsubscription typically
    const subscriptionDetails = subscription.toJSON();
    try {
        const response = await fetch(PUSH_UNSUBSCRIBE_URL, {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json',
            },
            body: JSON.stringify({ endpoint: subscriptionDetails.endpoint }),
        });
        if (!response.ok) {
            throw new Error(`Backend unsubscription failed: ${response.statusText}`);
        }
        console.log('Unsubscription sent to backend successfully.');
    } catch (error) {
        console.error('Error sending unsubscription to backend:', error);
        // Note: If backend unsubscription fails, the user is still unsubscribed on the client.
        // This might lead to orphaned subscriptions on the server if not handled.
    }
}


// Initialize push notifications
async function initializePushNotifications() {
  const reg = await registerServiceWorker();
  if (!reg) return; // Stop if service worker registration fails

  // Check current subscription state
  const currentSubscription = await reg.pushManager.getSubscription();
  isSubscribed = !(currentSubscription === null);
  updateSubscriptionButton();

  if (isSubscribed) {
    console.log('User IS already subscribed.');
    // Optional: You might want to re-send the subscription to your backend
    // here to ensure it's up-to-date, especially if the VAPID key changed.
    // await sendSubscriptionToBackend(currentSubscription);
  } else {
    console.log('User is NOT subscribed.');
  }
}

// --- UI Interaction ---

function updatePushToggleButtonState(buttonElement, serverPushEnabled) {
  if (!buttonElement) return;

  // Reflect browser's actual permission and subscription state primarily for enabling/disabling the button action.
  // The toggle's "checked" state should align with the server setting (`push_notifications_enabled`).

  buttonElement.checked = serverPushEnabled; // Align with server setting

  if (Notification.permission === 'denied') {
    // If permission is hard denied by the browser, the toggle action is effectively blocked.
    // We might want to disable the toggle or provide feedback.
    // For now, the 'checked' state still reflects server preference, but clicking it might not succeed.
    console.warn('Push notifications are blocked by the browser.');
    // buttonElement.disabled = true; // Optionally disable if permission is denied.
  } else {
    // buttonElement.disabled = false;
  }
  // The text content of the label for the switch usually doesn't change, only the checked state.
}


async function handlePushNotificationsToggle(event, serverPushEnabledInitially) {
  const toggleSwitch = event.target; // This should be the 'pushNotificationsToggle' input
  const wantsToEnable = toggleSwitch.checked;

  console.log(`Push toggle clicked. Wants to enable: ${wantsToEnable}. Currently subscribed (browser): ${isSubscribed}. Server setting was: ${serverPushEnabledInitially}`);

  if (wantsToEnable) {
    if (Notification.permission === 'denied') {
        alert('Browser notification permission is denied. Please enable it in your browser settings.');
        toggleSwitch.checked = false; // Revert toggle as action cannot proceed
        return false; // Indicate save should not proceed with this change
    }
    if (!isSubscribed) {
        const permission = await requestNotificationPermission();
        if (permission === 'granted') {
            await subscribeUserToPush(); // This will set isSubscribed = true and update UI
        } else {
            console.warn('Notification permission was not granted.');
            alert('Notification permission is required to enable push notifications.');
            toggleSwitch.checked = false; // Revert toggle
            return false; // Indicate save should not proceed with this change
        }
    }
    // If already subscribed, and user is enabling, all good.
  } else { // User wants to disable
    if (isSubscribed) {
        await unsubscribeUserFromPush(); // This will set isSubscribed = false and update UI
    }
    // If not subscribed, and user is disabling, all good.
  }
  return true; // Indicate that the state (for saving) is now reflected by toggleSwitch.checked
}


// Initialize when the script loads
// It's better to call this from a user interaction (e.g. settings page loaded)
// or after DOMContentLoaded if it's for a general button.
// For now, let's assume `initializePushNotifications` will be called
// when the relevant UI (e.g., settings page) is ready.
// Example: if (document.readyState === 'loading') {
// document.addEventListener('DOMContentLoaded', initializePushNotifications);
// } else {
// initializePushNotifications();
// }
//
// And the button click handler:
// const pushButton = document.getElementById('pushButton');
// if (pushButton) {
//   pushButton.addEventListener('click', handlePushButtonClick);
// }

// Initial call to set up service worker and check subscription state
// This should ideally be tied to when the settings page is loaded or a specific user action.
// For now, we'll call it.
// initializePushNotifications(); // Deferred to settings.js

console.log("notifications.js loaded");

// Export functions to be used by settings.js or other scripts
window.pushNotificationManager = {
    initialize: initializePushNotifications,
    handlePushNotificationsToggle: handlePushNotificationsToggle, // Renamed from handleToggle
    isSubscribed: () => isSubscribed, // Getter for subscription state
    getServiceWorkerRegistration: () => swRegistration,
    updatePushToggleButtonState: updatePushToggleButtonState, // Expose UI update function
    requestNotificationPermission: requestNotificationPermission, // Expose for direct call if needed
    subscribeUserToPush: subscribeUserToPush, // Expose for direct call if needed
    unsubscribeUserFromPush: unsubscribeUserFromPush, // Expose for direct call if needed

    // Simplified UI update based on current browser subscription and permission
    // This is called internally by subscribe/unsubscribe, but can be called externally too.
    // The `serverPushEnabled` parameter is for the toggle's checked state.
    updateUIAfterAction: (serverPushEnabled) => {
        const toggleButton = document.getElementById('pushNotificationsToggle');
        if (toggleButton) {
            updatePushToggleButtonState(toggleButton, serverPushEnabled);
        }
    }
};

// The old updateSubscriptionButton is effectively replaced by updatePushToggleButtonState
// and how it's called from settings.js.
// Keeping this function definition to avoid breaking any explicit calls if they were missed,
// but it should ideally be removed or refactored if not used.
function updateSubscriptionButton() {
    console.warn("updateSubscriptionButton directly called in notifications.js - this should be handled by settings.js through updatePushToggleButtonState");
    // const toggleButton = document.getElementById('pushNotificationsToggle');
    // if (toggleButton && window.currentServerSettings) {
    //      updatePushToggleButtonState(toggleButton, window.currentServerSettings.push_notifications_enabled);
    // }
}
