alert('JS loaded!');

document.addEventListener('DOMContentLoaded', function () {
    const settingsForm = document.getElementById('settingsForm'); // Ensure your form has id="settingsForm"
    const emailNotificationsToggle = document.getElementById('emailNotificationsToggle');
    const emailIntervalInput = document.getElementById('emailInterval');
    const recipientEmailInput = document.getElementById('recipientEmailInput');
    const pushNotificationsToggle = document.getElementById('pushNotificationsToggle');
    const pushIntervalInput = document.getElementById('pushInterval');
    const alertContainer = document.getElementById('alertContainer');
    let currentServerSettings = {}; // To store loaded settings

    // Function to display alerts
    function showAlert(message, type = 'success') {
        if (!alertContainer) return;
        const alertDiv = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        alertContainer.innerHTML = alertDiv;
    }

    // Load current settings
    console.log('Attempting to load current settings...');
    fetch('/api/settings')
        .then(response => {
            if (!response.ok) {
                console.error('Failed to fetch settings, status:', response.status);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(settings => {
            console.log('Received settings:', settings);
            emailNotificationsToggle.checked = settings.email_notifications_enabled === true;
            emailIntervalInput.value = settings.email_reminder_interval_minutes || 60;
            recipientEmailInput.value = settings.recipient_email || '';

            // Load push notification settings
            pushNotificationsToggle.checked = settings.push_notifications_enabled === true;
            pushIntervalInput.value = settings.push_notification_interval_minutes || 60;
            currentServerSettings = settings; // Store loaded settings

            console.log('Applied settings to form elements. Email Toggle:', emailNotificationsToggle.checked, 'Email Interval:', emailIntervalInput.value, 'Recipient Email:', recipientEmailInput.value, 'Push Toggle:', pushNotificationsToggle.checked, 'Push Interval:', pushIntervalInput.value);

            // Initialize Push Notification Manager and UI
            if (window.pushNotificationManager) {
                window.pushNotificationManager.initialize()
                    .then(() => {
                        // Update toggle state based on both server setting and current browser subscription status
                        // The initialize function in notifications.js already calls updateSubscriptionButton
                        // which now uses window.currentServerSettings.
                        // We just need to ensure the toggle reflects the server's preference initially.
                        window.pushNotificationManager.updatePushToggleButtonState(
                            pushNotificationsToggle,
                            currentServerSettings.push_notifications_enabled
                        );
                    });
            }
        })
        .catch(error => {
            console.error('Error loading settings:', error);
            showAlert('Failed to load current settings. Please try again later.', 'danger');
        });

    // Add event listener for the push notifications toggle
    if (pushNotificationsToggle && window.pushNotificationManager) {
        pushNotificationsToggle.addEventListener('change', async function(event) {
            // Store the initial server setting for push_notifications_enabled
            const initialServerPushEnabled = currentServerSettings.push_notifications_enabled;
            const successfulToggle = await window.pushNotificationManager.handlePushNotificationsToggle(event, initialServerPushEnabled);

            if (!successfulToggle) {
                // If handlePushNotificationsToggle returned false (e.g. permission denied and toggle reverted),
                // ensure our currentServerSettings reflects that the state wasn't *successfully* changed to the new toggle value.
                // The toggle itself is already reverted by handlePushNotificationsToggle.
                // We need to make sure that if save is hit now, it saves the *original* state if the toggle action failed.
                // This is tricky. For now, the save function will just read the current .checked state.
                // The handlePushNotificationsToggle already reverts the .checked state on failure.
            }
            // The push_notifications_enabled for saving will be based on the final state of pushNotificationsToggle.checked
        });
    }

    // Handle form submission
    if (settingsForm) {
        settingsForm.addEventListener('submit', function (event) {
            event.preventDefault();
            alertContainer.innerHTML = ''; // Clear previous alerts
            console.log('[DEBUG] Settings form submitted.');

            const emailIntervalValue = parseInt(emailIntervalInput.value, 10);
            const pushIntervalValue = parseInt(pushIntervalInput.value, 10);

            // The push_notifications_enabled state is now directly from the toggle's current state
            // which should have been managed by handlePushNotificationsToggle
            const finalPushEnabledState = pushNotificationsToggle.checked;

            const settingsData = {
                email_notifications_enabled: emailNotificationsToggle.checked,
                email_reminder_interval_minutes: emailIntervalValue,
                recipient_email: recipientEmailInput.value.trim(),
                push_notifications_enabled: finalPushEnabledState, // Use the toggle's current state
                push_notification_interval_minutes: pushIntervalValue
            };
            console.log('[DEBUG] Data to be sent:', settingsData);

            // Basic client-side validation for email interval
            if (isNaN(settingsData.email_reminder_interval_minutes) || settingsData.email_reminder_interval_minutes <= 0) {
                console.warn('[DEBUG] Validation failed: Email interval must be a positive number. Value:', settingsData.email_reminder_interval_minutes);
                showAlert('Email reminder interval must be a positive number.', 'danger');
                return;
            }
            // Basic client-side validation for push interval
            if (isNaN(settingsData.push_notification_interval_minutes) || settingsData.push_notification_interval_minutes <= 0) {
                console.warn('[DEBUG] Validation failed: Push notification interval must be a positive number. Value:', settingsData.push_notification_interval_minutes);
                showAlert('Push notification interval must be a positive number.', 'danger');
                return;
            }
            console.log('[DEBUG] Client-side validation passed.');

            const fetchOptions = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settingsData),
            };

            console.log('[DEBUG] Preparing to send settings. Options:', JSON.stringify(fetchOptions, null, 2)); // Log the options

            fetch('/api/settings', fetchOptions)
            .then(async response => {
                let body;
                try {
                    body = await response.json();
                } catch (e) {
                    body = { error: '[DEBUG] Could not parse JSON response', raw: await response.text() };
                }
                console.log('[DEBUG] Received response:', response.status, body);
                return { status: response.status, body };
            })
            .then(({ status, body }) => {
                if (status === 200 && body.message) {
                    showAlert(body.message, 'success');
                    console.log('[DEBUG] Settings saved successfully:', body.settings);
                } else if (body.error) {
                    showAlert(`[DEBUG] Error: ${body.error}`, 'danger');
                    console.error('[DEBUG] Error response from backend:', body.error);
                } else {
                    showAlert('[DEBUG] An unknown error occurred while saving settings.', 'danger');
                    console.error('[DEBUG] Unknown error, response body:', body);
                }
            })
            .catch(error => {
                console.error('[DEBUG] Error saving settings:', error);
                showAlert('[DEBUG] Failed to save settings. Check console for details.', 'danger');
            });
        });
    }
});
