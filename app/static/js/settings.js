document.addEventListener('DOMContentLoaded', function () {
    const settingsForm = document.getElementById('settingsForm'); // Ensure your form has id="settingsForm"
    const emailNotificationsToggle = document.getElementById('emailNotificationsToggle');
    const emailIntervalInput = document.getElementById('emailInterval');
    const recipientEmailInput = document.getElementById('recipientEmailInput');
    const pushNotificationsToggle = document.getElementById('pushNotificationsToggle');
    const pushIntervalInput = document.getElementById('pushInterval');
    const alertContainer = document.getElementById('alertContainer');

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
            pushIntervalInput.value = settings.push_notification_interval_minutes || 60; // Default to 60 if undefined

            console.log('Applied settings to form elements. Email Toggle:', emailNotificationsToggle.checked, 'Email Interval:', emailIntervalInput.value, 'Recipient Email:', recipientEmailInput.value, 'Push Toggle:', pushNotificationsToggle.checked, 'Push Interval:', pushIntervalInput.value);
        })
        .catch(error => {
            console.error('Error loading settings:', error);
            showAlert('Failed to load current settings. Please try again later.', 'danger');
        });

    // Handle form submission
    if (settingsForm) {
        settingsForm.addEventListener('submit', function (event) {
            event.preventDefault();
            alertContainer.innerHTML = ''; // Clear previous alerts
            console.log('Settings form submitted.');

            const emailIntervalValue = parseInt(emailIntervalInput.value, 10);
            const pushIntervalValue = parseInt(pushIntervalInput.value, 10);

            const settingsData = {
                email_notifications_enabled: emailNotificationsToggle.checked,
                email_reminder_interval_minutes: emailIntervalValue,
                recipient_email: recipientEmailInput.value.trim(),
                push_notifications_enabled: pushNotificationsToggle.checked,
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

            fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settingsData),
            })
            .then(response => response.json().then(data => ({ status: response.status, body: data })))
            .then(({ status, body }) => {
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
