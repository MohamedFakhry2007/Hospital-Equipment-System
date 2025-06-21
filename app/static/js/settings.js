document.addEventListener('DOMContentLoaded', function () {
    console.log('settings.js loaded successfully');

    const settingsForm = document.getElementById('settingsForm');
    const emailNotificationsToggle = document.getElementById('emailNotificationsToggle');
    const emailIntervalInput = document.getElementById('emailInterval');
    const recipientEmailInput = document.getElementById('recipientEmailInput');
    const pushNotificationsToggle = document.getElementById('pushNotificationsToggle');
    const pushIntervalInput = document.getElementById('pushInterval');
    const alertContainer = document.getElementById('alertContainer');
    let currentServerSettings = {};

    function showAlert(message, type = 'success') {
        if (!alertContainer) {
            console.error('Alert container not found');
            return;
        }
        const alertDiv = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        alertContainer.innerHTML = alertDiv;
    }

    if (!settingsForm || !emailNotificationsToggle || !emailIntervalInput || !recipientEmailInput || !pushNotificationsToggle || !pushIntervalInput) {
        console.error('One or more form elements not found:', {
            settingsForm: !!settingsForm,
            emailNotificationsToggle: !!emailNotificationsToggle,
            emailIntervalInput: !!emailIntervalInput,
            recipientEmailInput: !!recipientEmailInput,
            pushNotificationsToggle: !!pushNotificationsToggle,
            pushIntervalInput: !!pushIntervalInput
        });
        showAlert('Form initialization failed. Please refresh the page.', 'danger');
        return;
    }

    console.log('All form elements found successfully');

    fetch('/api/settings', { headers: { 'Accept': 'application/json' } })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return response.json();
        })
        .then(settings => {
            console.log('Settings loaded:', settings);
            emailNotificationsToggle.checked = !!settings.email_notifications_enabled;
            emailIntervalInput.value = settings.email_reminder_interval_minutes || 60;
            recipientEmailInput.value = settings.recipient_email || '';
            pushNotificationsToggle.checked = !!settings.push_notifications_enabled;
            pushIntervalInput.value = settings.push_notification_interval_minutes || 60;
            currentServerSettings = settings;

            if (window.pushNotificationManager) {
                window.pushNotificationManager.initialize()
                    .then(() => {
                        window.pushNotificationManager.updatePushToggleButtonState(
                            pushNotificationsToggle,
                            currentServerSettings.push_notifications_enabled
                        );
                    })
                    .catch(error => {
                        console.error('Error initializing push notifications:', error);
                        showAlert('Failed to initialize push notifications.', 'warning');
                    });
            }
        })
        .catch(error => {
            console.error('Error loading settings:', error);
            showAlert('Failed to load settings. Using default values.', 'warning');
        });

    if (pushNotificationsToggle && window.pushNotificationManager) {
        pushNotificationsToggle.addEventListener('change', async function (event) {
            console.log('Push notifications toggle changed:', event.target.checked);
            const initialServerPushEnabled = currentServerSettings.push_notifications_enabled;
            const successfulToggle = await window.pushNotificationManager.handlePushNotificationsToggle(event, initialServerPushEnabled);
            if (!successfulToggle) {
                console.log('Push toggle reverted due to failure');
            }
        });
    }

    settingsForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        console.log('Form submission triggered');
        alertContainer.innerHTML = '';

        const settingsData = {
            email_notifications_enabled: emailNotificationsToggle.checked,
            email_reminder_interval_minutes: parseInt(emailIntervalInput.value, 10),
            recipient_email: recipientEmailInput.value.trim(),
            push_notifications_enabled: pushNotificationsToggle.checked,
            push_notification_interval_minutes: parseInt(pushIntervalInput.value, 10)
        };
        console.log('Settings data to send:', settingsData);

        if (isNaN(settingsData.email_reminder_interval_minutes) || settingsData.email_reminder_interval_minutes <= 0) {
            console.warn('Invalid email interval:', settingsData.email_reminder_interval_minutes);
            showAlert('Email reminder interval must be a positive number.', 'danger');
            return;
        }
        if (isNaN(settingsData.push_notification_interval_minutes) || settingsData.push_notification_interval_minutes <= 0) {
            console.warn('Invalid push interval:', settingsData.push_notification_interval_minutes);
            showAlert('Push notification interval must be a positive number.', 'danger');
            return;
        }
        console.log('Client-side validation passed');

        try {
            const response = await fetch("/settings", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(settingsData),
                redirect: 'manual'
            });

            console.log('Fetch response status:', response.status, 'Type:', response.type);

            if (response.type === 'opaqueredirect') {
                showAlert('Settings saved. Reloading...', 'success');
                setTimeout(() => window.location.reload(), 1000);
                return;
            }

            const contentType = response.headers.get('content-type');
            let body;
            if (contentType && contentType.includes('application/json')) {
                body = await response.json();
            } else {
                body = { message: await response.text() };
            }

            if (response.ok) {
                console.log('Settings saved successfully:', body);
                showAlert(body.message || 'Settings saved successfully!', 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                console.error('Error saving settings:', body);
                showAlert(body.message || `Error saving settings (Status: ${response.status})`, 'danger');
            }
        } catch (error) {
            console.error('Fetch error:', error);
            showAlert('Failed to save settings. Please try again.', 'danger');
        }
    });
});
