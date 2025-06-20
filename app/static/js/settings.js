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
            console.log('Settings form submitted.');

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
            console.log('Data to be sent:', settingsData);

            // Basic client-side validation for email interval
            if (isNaN(settingsData.email_reminder_interval_minutes) || settingsData.email_reminder_interval_minutes <= 0) {
                console.warn('Validation failed: Email interval must be a positive number. Value:', settingsData.email_reminder_interval_minutes);
                showAlert('Email reminder interval must be a positive number.', 'danger');
                return;
            }
            // Basic client-side validation for push interval
            if (isNaN(settingsData.push_notification_interval_minutes) || settingsData.push_notification_interval_minutes <= 0) {
                console.warn('Validation failed: Push notification interval must be a positive number. Value:', settingsData.push_notification_interval_minutes);
                showAlert('Push notification interval must be a positive number.', 'danger');
                return;
            }
            console.log('Client-side validation passed.');

            const fetchOptions = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settingsData),
            };

            console.log('Preparing to send settings. Options:', JSON.stringify(fetchOptions, null, 2)); // Log the options

            fetch(settingsForm.action, fetchOptions) // Use the form's action URL
            .then(response => {
                // Check if the response is JSON before trying to parse it
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.indexOf("application/json") !== -1) {
                    return response.json().then(data => ({ status: response.status, body: data, ok: response.ok }));
                } else {
                    // If not JSON, it might be a redirect page or HTML error, get text
                    return response.text().then(text => ({ status: response.status, body: { error: `Unexpected response type: ${contentType}. Response text: ${text.substring(0, 200)}...` }, ok: response.ok }));
                }
            })
            .then(({ status, body, ok }) => { // Added 'ok' from response
                // The save_settings_page in views.py redirects on success/flash,
                // so a 200 OK with JSON might not be the typical success case if it redirects.
                // However, if it processes JSON and returns JSON (like api.py's version), this logic is fine.
                // Given the flash message "Invalid request format. Expected JSON." comes from views.py,
                // and it redirects, a successful JSON POST to it might also result in a redirect (e.g., 302).
                // Fetch API by default does not follow redirects if the method is POST, unless `redirect: 'follow'` is set.
                // If views.save_settings_page returns a JSON response directly on success, this is fine.
                // If it redirects, the browser will handle the redirect (typically as a GET),
                // and this .then() block might not see the "final" page content directly from the POST.
                // For now, assume it might return JSON or an error in JSON.

                if (ok && body.message) { // Check response.ok for success (status 200-299)
                    showAlert(body.message, 'success');
                    // If views.save_settings_page redirects, the user will see the new page.
                    // If it returns JSON, this alert is shown.
                    // To ensure settings are re-loaded on success if it doesn't redirect:
                    // window.location.reload(); // Or update currentServerSettings and form fields
                } else if (body.error) {
                    showAlert(`Error: ${body.error}`, 'danger');
                } else if (!ok) { // Handle other non-successful statuses that weren't JSON errors
                    showAlert(`An error occurred while saving settings. Status: ${status}`, 'danger');
                } else { // Fallback for unexpected successful response structure
                    showAlert('Settings saved, but response format was unexpected.', 'warning');
                }
                if (status === 200 && body.message) {
                    showAlert(body.message, 'success');
                } else if (body.error) {
                    showAlert(`Error: ${body.error}`, 'danger');
                } else {
                    showAlert('An unknown error occurred while saving settings.', 'danger');
                }
            })
            .catch(error => {
                console.error('Error saving settings:', error);
                showAlert('Failed to save settings. Check console for details.', 'danger');
            });
        });
    }
});
