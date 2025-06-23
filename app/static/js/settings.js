document.addEventListener('DOMContentLoaded', function () {
    console.log('settings.js loaded successfully');

    // Legacy form elements
    const settingsForm = document.getElementById('settingsForm');
    const emailNotificationsToggle = document.getElementById('emailNotificationsToggle');
    const emailIntervalInput = document.getElementById('emailInterval');
    const recipientEmailInput = document.getElementById('receiverEmail'); // Fixed: use correct ID
    const pushNotificationsToggle = document.getElementById('pushNotificationsToggle');
    const pushIntervalInput = document.getElementById('pushInterval');
    
    // New form elements
    const reminder60Days = document.getElementById('reminder60Days');
    const reminder14Days = document.getElementById('reminder14Days');
    const reminder1Day = document.getElementById('reminder1Day');
    const schedulerInterval = document.getElementById('schedulerInterval');
    const enableAutomaticReminders = document.getElementById('enableAutomaticReminders');
    const receiverEmail = document.getElementById('receiverEmail');
    const ccEmails = document.getElementById('ccEmails');
    
    // New buttons
    const saveReminderSettings = document.getElementById('saveReminderSettings');
    const saveEmailSettings = document.getElementById('saveEmailSettings');
    const sendTestEmail = document.getElementById('sendTestEmail');
    const sendTestPush = document.getElementById('sendTestPush');
    const resetAllSettings = document.getElementById('resetAllSettings');
    
    // Backup settings elements
    const automaticBackupToggle = document.getElementById('automaticBackupToggle');
    const backupInterval = document.getElementById('backupInterval');
    
    const alertContainer = document.getElementById('alertContainer');
    let currentServerSettings = {};

    // Enhanced alert function with better styling and auto-dismiss
    function showAlert(message, type = 'success', duration = 5000) {
        if (!alertContainer) {
            console.error('Alert container not found');
            return;
        }
        
        // Clear existing alerts
        alertContainer.innerHTML = '';
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas ${getAlertIcon(type)} me-3"></i>
                <div class="flex-grow-1">
                    <strong>${getAlertTitle(type)}</strong>
                    <div>${message}</div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertContainer.appendChild(alertDiv);
        
        // Auto-dismiss after duration
        if (duration > 0) {
            setTimeout(() => {
                if (alertDiv && alertDiv.parentNode) {
                    alertDiv.classList.remove('show');
                    setTimeout(() => {
                        if (alertDiv.parentNode) {
                            alertDiv.parentNode.removeChild(alertDiv);
                        }
                    }, 150);
                }
            }, duration);
        }
    }

    function getAlertIcon(type) {
        const icons = {
            'success': 'fa-check-circle',
            'danger': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-circle',
            'info': 'fa-info-circle'
        };
        return icons[type] || 'fa-info-circle';
    }

    function getAlertTitle(type) {
        const titles = {
            'success': 'Success!',
            'danger': 'Error!',
            'warning': 'Warning!',
            'info': 'Info'
        };
        return titles[type] || 'Notice';
    }

    // Loading state management
    function setButtonLoading(button, loading = true) {
        if (!button) return;
        
        if (loading) {
            button.disabled = true;
            button.classList.add('loading');
            button.dataset.originalText = button.innerHTML;
        } else {
            button.disabled = false;
            button.classList.remove('loading');
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
            }
        }
    }

    // Show toast notification
    function showToast(message, type = 'success') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1055';
            document.body.appendChild(toastContainer);
        }

        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas ${getAlertIcon(type)} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: 4000 });
        toast.show();

        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
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

    // Load settings from server
    fetch('/api/settings', { headers: { 'Accept': 'application/json' } })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return response.json();
        })
        .then(settings => {
            console.log('Settings loaded:', settings);
            
            // Legacy settings
            if (emailNotificationsToggle) emailNotificationsToggle.checked = !!settings.email_notifications_enabled;
            if (emailIntervalInput) emailIntervalInput.value = settings.email_reminder_interval_minutes || 60;
            if (recipientEmailInput) recipientEmailInput.value = settings.recipient_email || '';
            if (pushNotificationsToggle) pushNotificationsToggle.checked = !!settings.push_notifications_enabled;
            if (pushIntervalInput) pushIntervalInput.value = settings.push_notification_interval_minutes || 60;
            
            // New reminder settings
            if (reminder60Days) reminder60Days.checked = settings.reminder_timing?.['60_days_before'] || false;
            if (reminder14Days) reminder14Days.checked = settings.reminder_timing?.['14_days_before'] || false;
            if (reminder1Day) reminder1Day.checked = settings.reminder_timing?.['1_day_before'] || false;
            if (schedulerInterval) schedulerInterval.value = settings.scheduler_interval_hours || 24;
            if (enableAutomaticReminders) enableAutomaticReminders.checked = !!settings.enable_automatic_reminders;
            
            // New email settings
            if (receiverEmail) receiverEmail.value = settings.recipient_email || '';
            if (ccEmails) ccEmails.value = settings.cc_emails || '';
            
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

    // Push notifications toggle handler
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

    // Save Settings Button Click Handler
    const saveSettingsButton = document.getElementById('saveSettingsButton');
    if (saveSettingsButton) {
        saveSettingsButton.addEventListener('click', async function (event) {
            event.preventDefault();
            console.log('Save settings button clicked');
            
            setButtonLoading(saveSettingsButton, true);

        // Get email send time from the form
        const emailSendTimeElement = document.getElementById('emailSendTime');
        const emailSendTimeHour = emailSendTimeElement ? parseInt(emailSendTimeElement.value, 10) : 7;

        const settingsData = {
            email_notifications_enabled: emailNotificationsToggle.checked,
            email_reminder_interval_minutes: parseInt(emailIntervalInput.value, 10),
            email_send_time_hour: emailSendTimeHour,
            recipient_email: recipientEmailInput.value.trim(),
            push_notifications_enabled: pushNotificationsToggle.checked,
            push_notification_interval_minutes: parseInt(pushIntervalInput.value, 10)
        };
        console.log('Settings data to send:', settingsData);

        if (isNaN(settingsData.email_reminder_interval_minutes) || settingsData.email_reminder_interval_minutes <= 0) {
            console.warn('Invalid email interval:', settingsData.email_reminder_interval_minutes);
            showAlert('Email reminder interval must be a positive number.', 'danger');
            setButtonLoading(saveSettingsButton, false);
            return;
        }
        if (isNaN(settingsData.push_notification_interval_minutes) || settingsData.push_notification_interval_minutes <= 0) {
            console.warn('Invalid push interval:', settingsData.push_notification_interval_minutes);
            showAlert('Push notification interval must be a positive number.', 'danger');
            setButtonLoading(saveSettingsButton, false);
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
                showToast('System settings saved successfully!', 'success');
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
                showToast('System settings saved successfully!', 'success');
                showAlert(body.message || 'Settings saved successfully!', 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                console.error('Error saving settings:', body);
                showAlert(body.message || `Error saving settings (Status: ${response.status})`, 'danger');
            }
        } catch (error) {
            console.error('Fetch error:', error);
            showAlert('Failed to save settings. Please try again.', 'danger');
        } finally {
            setButtonLoading(saveSettingsButton, false);
        }
        });
    }

    // New reminder settings handler
    if (saveReminderSettings) {
        saveReminderSettings.addEventListener('click', async function(event) {
            event.preventDefault();
            
            setButtonLoading(saveReminderSettings, true);

            const reminderData = {
                reminder_timing_60_days: reminder60Days ? reminder60Days.checked : false,
                reminder_timing_14_days: reminder14Days ? reminder14Days.checked : false,
                reminder_timing_1_day: reminder1Day ? reminder1Day.checked : false,
                scheduler_interval_hours: schedulerInterval ? parseInt(schedulerInterval.value, 10) : 24,
                enable_automatic_reminders: enableAutomaticReminders ? enableAutomaticReminders.checked : false
            };

            console.log('Reminder settings data to send:', reminderData);

            if (isNaN(reminderData.scheduler_interval_hours) || reminderData.scheduler_interval_hours <= 0 || reminderData.scheduler_interval_hours > 168) {
                showAlert('Scheduler interval must be between 1-168 hours.', 'danger');
                setButtonLoading(saveReminderSettings, false);
                return;
            }

            try {
                const response = await fetch('/settings/reminder', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(reminderData)
                });

                const result = await response.json();

                if (response.ok) {
                    showToast('Reminder settings saved successfully!', 'success');
                    showAlert('Reminder settings saved successfully!', 'success');
                    currentServerSettings = { ...currentServerSettings, ...reminderData };
                } else {
                    showAlert(result.error || result.message || 'Failed to save reminder settings.', 'danger');
                }
            } catch (error) {
                console.error('Error saving reminder settings:', error);
                showAlert('Failed to save reminder settings. Please try again.', 'danger');
            } finally {
                setButtonLoading(saveReminderSettings, false);
            }
        });
    }

    // New email settings handler
    if (saveEmailSettings) {
        saveEmailSettings.addEventListener('click', async function(event) {
            event.preventDefault();
            
            setButtonLoading(saveEmailSettings, true);

            const emailData = {
                recipient_email: receiverEmail ? receiverEmail.value.trim() : '',
                cc_emails: ccEmails ? ccEmails.value.trim() : ''
            };

            // Basic email validation
            if (emailData.recipient_email && !isValidEmail(emailData.recipient_email)) {
                showAlert('Please enter a valid primary email address.', 'danger');
                setButtonLoading(saveEmailSettings, false);
                return;
            }

            // Validate CC emails
            if (emailData.cc_emails) {
                const ccEmailList = emailData.cc_emails.split(',').map(email => email.trim());
                for (let email of ccEmailList) {
                    if (email && !isValidEmail(email)) {
                        showAlert(`Invalid CC email address: ${email}`, 'danger');
                        setButtonLoading(saveEmailSettings, false);
                        return;
                    }
                }
            }

            try {
                const response = await fetch('/settings/email', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(emailData)
                });

                const result = await response.json();

                if (response.ok) {
                    showToast('Email settings saved successfully!', 'success');
                    showAlert('Email settings saved successfully!', 'success');
                    currentServerSettings = { ...currentServerSettings, ...emailData };
                } else {
                    showAlert(result.error || result.message || 'Failed to save email settings.', 'danger');
                }
            } catch (error) {
                console.error('Error saving email settings:', error);
                showAlert('Failed to save email settings. Please try again.', 'danger');
            } finally {
                setButtonLoading(saveEmailSettings, false);
            }
        });
    }

    // Send test email handler
    if (sendTestEmail) {
        sendTestEmail.addEventListener('click', async function(event) {
            event.preventDefault();
            
            setButtonLoading(sendTestEmail, true);

            try {
                const response = await fetch('/settings/test-email', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        recipient_email: receiverEmail ? receiverEmail.value.trim() : '',
                        cc_emails: ccEmails ? ccEmails.value.trim() : ''
                    })
                });

                const result = await response.json();

                if (response.ok) {
                    showToast('Test email sent successfully!', 'success');
                    showAlert('Test email sent successfully! Check your inbox.', 'success');
                } else {
                    showAlert(result.error || result.message || 'Failed to send test email.', 'danger');
                }
            } catch (error) {
                console.error('Error sending test email:', error);
                showAlert('Failed to send test email. Please try again.', 'danger');
            } finally {
                setButtonLoading(sendTestEmail, false);
            }
        });
    }

    // Send test push notification handler
    if (sendTestPush) {
        sendTestPush.addEventListener('click', async function(event) {
            event.preventDefault();
            
            setButtonLoading(sendTestPush, true);

            try {
                const response = await fetch('/api/test-push', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });

                const result = await response.json();

                if (response.ok) {
                    showToast('Test push notification sent successfully!', 'success');
                    showAlert('Test push notification sent successfully! Check your desktop for the notification.', 'success');
                } else {
                    showAlert(result.error || result.message || 'Failed to send test push notification.', 'danger');
                }
            } catch (error) {
                console.error('Error sending test push notification:', error);
                showAlert('Failed to send test push notification. Please try again.', 'danger');
            } finally {
                setButtonLoading(sendTestPush, false);
            }
        });
    }

    // Reset all settings handler
    if (resetAllSettings) {
        resetAllSettings.addEventListener('click', function(event) {
            event.preventDefault();
            
            if (confirm('Are you sure you want to reset all settings to their default values? This action cannot be undone.')) {
                resetToDefaults();
            }
        });
    }

    // Email validation function
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Reset to defaults function
    function resetToDefaults() {
        const defaultSettings = {
            email_notifications_enabled: true,
            email_reminder_interval_minutes: 60,
            recipient_email: '',
            push_notifications_enabled: true,
            push_notification_interval_minutes: 60,
            reminder_timing_60_days: false,
            reminder_timing_14_days: false,
            reminder_timing_1_day: false,
            scheduler_interval_hours: 24,
            enable_automatic_reminders: false,
            cc_emails: ''
        };

        // Update form fields
        if (emailNotificationsToggle) emailNotificationsToggle.checked = defaultSettings.email_notifications_enabled;
        if (emailIntervalInput) emailIntervalInput.value = defaultSettings.email_reminder_interval_minutes;
        if (recipientEmailInput) recipientEmailInput.value = defaultSettings.recipient_email;
        if (pushNotificationsToggle) pushNotificationsToggle.checked = defaultSettings.push_notifications_enabled;
        if (pushIntervalInput) pushIntervalInput.value = defaultSettings.push_notification_interval_minutes;
        if (reminder60Days) reminder60Days.checked = defaultSettings.reminder_timing_60_days;
        if (reminder14Days) reminder14Days.checked = defaultSettings.reminder_timing_14_days;
        if (reminder1Day) reminder1Day.checked = defaultSettings.reminder_timing_1_day;
        if (schedulerInterval) schedulerInterval.value = defaultSettings.scheduler_interval_hours;
        if (enableAutomaticReminders) enableAutomaticReminders.checked = defaultSettings.enable_automatic_reminders;
        if (receiverEmail) receiverEmail.value = defaultSettings.recipient_email;
        if (ccEmails) ccEmails.value = defaultSettings.cc_emails;

        showToast('Settings reset to defaults', 'info');
        showAlert('All settings have been reset to their default values. Don\'t forget to save your changes!', 'info');
    }

    // Add visual feedback for form changes
    function addChangeListeners() {
        const allInputs = document.querySelectorAll('#settingsForm input, input[name^="reminder_"], input[name="recipient_email"], input[name="cc_emails"]');
        
        allInputs.forEach(input => {
            input.addEventListener('change', function() {
                // Add a subtle visual indicator that settings have changed
                this.classList.add('border-warning');
                setTimeout(() => {
                    this.classList.remove('border-warning');
                }, 2000);
            });
        });
    }

    // Initialize change listeners
    addChangeListeners();

    // ============================================================================
    // BACKUP FUNCTIONALITY
    // ============================================================================
    
    // Backup button handlers
    const createFullBackup = document.getElementById('createFullBackup');
    const createSettingsBackup = document.getElementById('createSettingsBackup');
    const refreshBackups = document.getElementById('refreshBackups');
    
    // Load backup settings
    if (automaticBackupToggle) {
        automaticBackupToggle.checked = currentServerSettings.automatic_backup_enabled || false;
    }
    if (backupInterval) {
        backupInterval.value = currentServerSettings.automatic_backup_interval_hours || 24;
    }
    
    // Create full backup handler
    if (createFullBackup) {
        createFullBackup.addEventListener('click', function(event) {
            event.preventDefault();
            
            if (confirm('Create a full application backup? This may take a few moments for large systems.')) {
                setButtonLoading(createFullBackup, true);
                
                // Submit the form
                const form = createFullBackup.closest('form');
                if (form) {
                    form.submit();
                }
            }
        });
    }
    
    // Create settings backup handler
    if (createSettingsBackup) {
        createSettingsBackup.addEventListener('click', function(event) {
            event.preventDefault();
            
            setButtonLoading(createSettingsBackup, true);
            
            // Submit the form
            const form = createSettingsBackup.closest('form');
            if (form) {
                form.submit();
            }
        });
    }
    
    // Save backup settings handler
    const saveBackupSettings = document.getElementById('saveBackupSettings');
    if (saveBackupSettings) {
        saveBackupSettings.addEventListener('click', async function(event) {
            event.preventDefault();
            
            setButtonLoading(saveBackupSettings, true);

            const backupData = {
                automatic_backup_enabled: automaticBackupToggle ? automaticBackupToggle.checked : false,
                automatic_backup_interval_hours: backupInterval ? parseInt(backupInterval.value, 10) : 24
            };

            console.log('Backup settings data to send:', backupData);

            if (isNaN(backupData.automatic_backup_interval_hours) || backupData.automatic_backup_interval_hours < 1 || backupData.automatic_backup_interval_hours > 168) {
                showAlert('Backup interval must be between 1-168 hours.', 'danger');
                setButtonLoading(saveBackupSettings, false);
                return;
            }

            try {
                const response = await fetch('/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(backupData)
                });

                if (response.type === 'opaqueredirect') {
                    showToast('Backup settings saved successfully!', 'success');
                    showAlert('Backup settings saved successfully!', 'success');
                    setTimeout(() => window.location.reload(), 1000);
                    return;
                }

                const result = await response.json();

                if (response.ok) {
                    showToast('Backup settings saved successfully!', 'success');
                    showAlert('Backup settings saved successfully!', 'success');
                    currentServerSettings = { ...currentServerSettings, ...backupData };
                } else {
                    showAlert(result.error || result.message || 'Failed to save backup settings.', 'danger');
                }
            } catch (error) {
                console.error('Error saving backup settings:', error);
                showAlert('Failed to save backup settings. Please try again.', 'danger');
            } finally {
                setButtonLoading(saveBackupSettings, false);
            }
        });
    }
    
    // Refresh backups handler
    if (refreshBackups) {
        refreshBackups.addEventListener('click', function(event) {
            event.preventDefault();
            loadBackupList();
        });
    }
    
    // Load backup list function
    function loadBackupList() {
        const backupListContainer = document.getElementById('backupList');
        if (!backupListContainer) return;
        
        // Show loading state
        backupListContainer.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-success" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted">Loading backups...</p>
            </div>
        `;
        
        fetch('/backup/list')
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    displayBackupList(data.backups);
                } else {
                    throw new Error(data.error || 'Failed to load backups');
                }
            })
            .catch(error => {
                console.error('Error loading backups:', error);
                backupListContainer.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-exclamation-triangle text-warning fa-2x"></i>
                        <p class="mt-2 text-muted">Error loading backups: ${error.message}</p>
                        <button type="button" class="btn btn-sm btn-outline-success" onclick="loadBackupList()">
                            <i class="fas fa-refresh me-1"></i>Try Again
                        </button>
                    </div>
                `;
            });
    }
    
    // Display backup list function
    function displayBackupList(backups) {
        const backupListContainer = document.getElementById('backupList');
        if (!backupListContainer) return;
        
        if (backups.length === 0) {
            backupListContainer.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-archive text-muted fa-2x"></i>
                    <p class="mt-2 text-muted">No backups found</p>
                    <small class="text-muted">Create your first backup using the buttons above</small>
                </div>
            `;
            return;
        }
        
        let tableHtml = `
            <table class="table table-striped table-hover">
                <thead class="table-success">
                    <tr>
                        <th>Type</th>
                        <th>Filename</th>
                        <th>Size</th>
                        <th>Created</th>
                        <th>Age</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        backups.forEach(backup => {
            const typeClass = backup.type === 'full' ? 'primary' : 'info';
            const typeIcon = backup.type === 'full' ? 'fa-archive' : 'fa-cog';
            const size = backup.type === 'full' ? `${backup.size_mb} MB` : `${backup.size_kb} KB`;
            const createdDate = new Date(backup.created_at).toLocaleString();
            const ageText = backup.age_days === 0 ? 'Today' : `${backup.age_days} day${backup.age_days !== 1 ? 's' : ''} ago`;
            
            tableHtml += `
                <tr>
                    <td>
                        <span class="badge bg-${typeClass}">
                            <i class="fas ${typeIcon} me-1"></i>
                            ${backup.type.toUpperCase()}
                        </span>
                    </td>
                    <td>
                        <code class="small">${backup.filename}</code>
                    </td>
                    <td>${size}</td>
                    <td>${createdDate}</td>
                    <td>
                        <small class="text-muted">${ageText}</small>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm" role="group">
                            <a href="/backup/download/${backup.type}/${backup.filename}" 
                               class="btn btn-outline-success btn-sm" 
                               title="Download">
                                <i class="fas fa-download"></i>
                            </a>
                            <button type="button" 
                                    class="btn btn-outline-danger btn-sm" 
                                    onclick="deleteBackup('${backup.filename}')"
                                    title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        tableHtml += `
                </tbody>
            </table>
        `;
        
        backupListContainer.innerHTML = tableHtml;
    }
    
    // Delete backup function (global scope for onclick handlers)
    window.deleteBackup = function(filename) {
        if (confirm(`Are you sure you want to delete the backup "${filename}"? This action cannot be undone.`)) {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/backup/delete/${filename}`;
            document.body.appendChild(form);
            form.submit();
        }
    };
    
    // Load backup list on page load
    setTimeout(() => {
        loadBackupList();
    }, 1000);
    
    // Make loadBackupList globally accessible
    window.loadBackupList = loadBackupList;

    console.log('Settings page initialization complete');
});
