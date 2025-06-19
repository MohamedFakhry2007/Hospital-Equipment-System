document.addEventListener('DOMContentLoaded', function () {
    const settingsForm = document.getElementById('settingsForm');
    const emailNotificationsToggle = document.getElementById('emailNotificationsToggle');
    const emailIntervalInput = document.getElementById('emailInterval');
    const recipientEmailInput = document.getElementById('recipientEmailInput'); // Added
    const alertContainer = document.getElementById('alertContainer'); // Assuming an alert container is added to HTML

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
            emailIntervalInput.value = settings.email_reminder_interval_minutes || 60; // Default to 60 if undefined
            recipientEmailInput.value = settings.recipient_email || ''; // Default to empty string
            console.log('Applied settings to form elements. Toggle checked:', emailNotificationsToggle.checked, 'Interval value:', emailIntervalInput.value, 'Recipient Email:', recipientEmailInput.value);
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

            const intervalValue = parseInt(emailIntervalInput.value, 10);
            console.log('Raw interval input value:', emailIntervalInput.value, 'Parsed interval value:', intervalValue);

            const settingsData = {
                email_notifications_enabled: emailNotificationsToggle.checked,
                email_reminder_interval_minutes: intervalValue,
                recipient_email: recipientEmailInput.value.trim() // Added
            };
            console.log('Data to be sent:', settingsData);

            // Basic client-side validation
            if (isNaN(settingsData.email_reminder_interval_minutes) || settingsData.email_reminder_interval_minutes <= 0) {
                console.warn('Validation failed: Email interval must be a positive number. Value:', settingsData.email_reminder_interval_minutes);
                showAlert('Email interval must be a positive number.', 'danger');
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
