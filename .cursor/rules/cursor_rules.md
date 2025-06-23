# Cursor AI Development Rules

## Flask Application Development Rules

### 🔄 **CRITICAL: Flask Application Restart Requirements**

**ALWAYS restart the Flask application when making changes to:**

#### **Python Code That REQUIRES Restart:**
- ✅ **Models** (`app/models/*.py`) - Pydantic validation, schema changes
- ✅ **Services** (`app/services/*.py`) - Business logic, data processing
- ✅ **Routes** (`app/routes/*.py`) - Endpoint logic, API handlers  
- ✅ **Configuration** (`app/config.py`) - Settings, environment variables
- ✅ **Main application** (`app/main.py`) - Core application setup
- ✅ **Validation logic** - Any Pydantic validators, custom validation functions
- ✅ **Database models** - SQLAlchemy models, schema definitions
- ✅ **Import statements** - New dependencies, module imports

#### **Files That DON'T Require Restart (Hot-Reload):**
- ❌ **Templates** (`app/templates/*.html`) - Jinja2 templates reload automatically
- ❌ **Static files** (`app/static/*.css`, `*.js`) - Served directly by Flask
- ❌ **JSON data files** (`data/*.json`) - Loaded dynamically by services

### 🚨 **Flask Restart Protocol:**

```bash
# 1. Stop all Python processes
taskkill /F /IM python.exe

# 2. Restart Flask application  
poetry run python app/main.py
```

### ⚠️ **Common Mistake to Avoid:**
- **DON'T assume Python code changes take effect immediately**
- **DON'T continue testing without restart** after model/service changes
- **DO verify logs show new behavior** after restart
- **DO check timestamps** in logs to confirm fresh application start

### 💡 **Best Practices:**
1. **Make Python code changes** in logical groups
2. **Restart Flask application** after each group of changes
3. **Verify changes took effect** by testing or checking logs
4. **Template/CSS changes** can be tested with browser refresh only

### 🐛 **Debugging Code Changes:**
If changes don't seem to work:
1. ✅ **Check if restart is needed** (Python code changes)
2. ✅ **Verify no syntax errors** in modified files  
3. ✅ **Check Flask logs** for error messages
4. ✅ **Confirm file saves** were successful
5. ✅ **Test with simple print statements** to verify code execution

---

## 🔄 **CRITICAL: Template Cloning and Dynamic Data Population**

### ⚠️ **Template `<template>` Tag Limitations:**
When using HTML `<template>` tags with JavaScript cloning, **Jinja2 templating does NOT work** for cloned content.

#### **The Problem:**
```html
<!-- ❌ THIS DOESN'T WORK for cloned content -->
<template id="machine-template">
    <select class="trainer-select">
        {% for trainer in trainers %}
            <option value="{{ trainer }}">{{ trainer }}</option>
        {% endfor %}
    </select>
</template>
```

#### **The Solution:**
```html
<!-- ✅ USE JAVASCRIPT TO POPULATE OPTIONS -->
<template id="machine-template">
    <select class="trainer-select">
        <option value="">Select Trainer</option>
        <!-- Options populated by JavaScript -->
    </select>
</template>

<script>
// Pass data to JavaScript
const trainers = {{ trainers|tojson }};

// Populate options when cloning
trainers.forEach(trainer => {
    const option = document.createElement('option');
    option.value = trainer;
    option.textContent = trainer;
    trainerSelect.appendChild(option);
});
</script>
```

### 🎯 **Template Cloning Best Practices:**
1. **Pass dynamic data to JavaScript** using `{{ data|tojson }}`
2. **Populate dropdown options via JavaScript** when cloning templates
3. **Test cloned elements** to ensure all dropdowns work correctly
4. **Use `document.createElement()` and `appendChild()`** for dynamic options
5. **Never rely on Jinja2 loops** inside `<template>` tags for cloned content

### 🚨 **Common Template Cloning Mistakes:**
- ❌ Using Jinja2 loops inside `<template>` tags
- ❌ Assuming server-side templating works for cloned content
- ❌ Not testing cloned dropdowns/forms
- ❌ Forgetting to pass data to JavaScript

---

## 🔄 **CRITICAL: Duplicate JavaScript Files Issue**

### ⚠️ **Duplicate Static Files Problem:**
This project has **DUPLICATE JavaScript files** in both `app/static/js/` and `static/js/` directories, which can cause variable conflicts and syntax errors.

#### **The Problem:**
```
app/static/js/equipment_list.js  ← Main file
static/js/equipment_list.js      ← Duplicate file (causes conflicts)
```

When both files are loaded:
- **Variable redeclaration errors**: `Identifier 'style' has already been declared`
- **Function conflicts**: Same functions defined multiple times
- **Unpredictable behavior**: Different versions of code running

#### **The Solution:**
1. **Always update BOTH files** when making JavaScript changes
2. **Use unique identifiers** to prevent conflicts
3. **Check for existing elements** before creating new ones

```javascript
// ✅ SAFE: Check if already exists before creating
if (!document.getElementById('equipment-table-styles')) {
    const style = document.createElement('style');
    style.id = 'equipment-table-styles';
    // ... rest of code
}

// ✅ SAFE: Early return if page doesn't need the script
const tableBody = document.querySelector('.equipment-table tbody');
if (!tableBody) {
    console.log('No equipment table found, skipping initialization');
    return;
}
```

### 🎯 **Duplicate Files Best Practices:**
1. **Always check for duplicate files** in both directories
2. **Update ALL copies** when making changes to JavaScript files
3. **Use defensive programming** with existence checks
4. **Add unique IDs** to dynamically created elements
5. **Test on different pages** to ensure no conflicts

### 🚨 **Files That Have Duplicates:**
- `equipment_list.js` - **UPDATE BOTH COPIES**
- `dashboard.js` - **UPDATE BOTH COPIES**
- `import_export.js` - **UPDATE BOTH COPIES**
- `main.js` - **UPDATE BOTH COPIES**
- `notifications.js` - **UPDATE BOTH COPIES**
- `service-worker.js` - **UPDATE BOTH COPIES**
- `settings.js` - **UPDATE BOTH COPIES**

### 🐛 **Debugging Duplicate File Issues:**
If you see JavaScript errors like:
- `Identifier 'X' has already been declared`
- `Function 'Y' is not defined` (inconsistent behavior)
- `Element not found` (script runs on wrong page)

**Solution Steps:**
1. ✅ **Check both directories** for duplicate files
2. ✅ **Update ALL copies** with the same changes
3. ✅ **Add defensive checks** for element existence
4. ✅ **Use unique IDs** for dynamically created elements
5. ✅ **Test on multiple pages** to verify no conflicts

---

## 🔄 **CRITICAL: Flask Data Import/Export Troubleshooting**

### ⚠️ **N/A Value Handling in CSV Imports**

When working with Flask applications that handle CSV import/export operations, especially for equipment management systems (PPM, OCM, Training), follow these critical patterns to avoid common data validation and processing issues:

#### **Data Validation Patterns:**

```python
# ✅ CORRECT: Comprehensive N/A handling in Pydantic validators
@field_validator('Installation_Date', 'Warranty_End')
@classmethod
def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
    """Validate date format while handling N/A values properly."""
    # Handle None, empty strings, AND N/A (case-insensitive)
    if v is None or not v.strip() or v.strip().upper() == 'N/A':
        return None  # Convert to None for consistent handling
    
    try:
        # Try DD/MM/YYYY format first (preferred)
        datetime.strptime(v, '%d/%m/%Y')
        return v
    except ValueError:
        # Add fallback formats as needed
        raise ValueError(f"Invalid date format: {v}. Expected format: DD/MM/YYYY")
```

#### **Data Transformation Best Practices:**

```python
# ✅ CORRECT: Helper function for data cleaning
def clean_value(value):
    """Convert N/A values to None at transformation layer."""
    if value is None or (isinstance(value, str) and (value.strip() == '' or value.strip().upper() == 'N/A')):
        return None
    return value

# ✅ CORRECT: Use dtype=str to prevent pandas auto-conversion
df = pd.read_csv(file_path, dtype=str)  # Prevents "4152" → "4152.0" conversion

# ✅ CORRECT: Clean data in transformation layer
result = {
    "Installation_Date": clean_value(flat_entry.get("Installation_Date")),
    "Warranty_End": clean_value(flat_entry.get("Warranty_End")),
    # ... other fields
}
```

### 🚨 **Import Service Architecture:**

#### **Consistent Error Handling:**
```python
# ✅ CORRECT: Detailed import feedback
def import_from_csv(file_path: str, data_type: str):
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process each row with proper error handling
    for index, row in df.iterrows():
        try:
            # Check for duplicates using key fields
            key_field = 'SERIAL' if data_type == 'ppm' else 'employee_id'
            if is_duplicate(row[key_field], existing_data):
                skipped_count += 1
                logger.warning(f"Skipping row {index}: Duplicate {key_field} {row[key_field]}")
                continue
                
            # Validate and import
            entry = validate_entry(row, data_type)
            save_entry(entry)
            imported_count += 1
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing row {index}: {e}")
    
    return {
        'success': error_count == 0,
        'message': f"Import complete. {imported_count} entries imported, {skipped_count} skipped, {error_count} errors.",
        'imported': imported_count,
        'skipped': skipped_count,
        'errors': error_count
    }
```

#### **AJAX Training Import Pattern:**
```javascript
// ✅ CORRECT: AJAX import with proper feedback
function handleTrainingImport(formData) {
    fetch('/import_equipment', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
        },
        body: formData
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new Error('Import failed with status: ' + response.status);
        }
    })
    .then(data => {
        if (data.success) {
            showSuccessMessage(data.message);
            // Add timestamp to force page refresh and counter update
            const redirectUrl = data.redirect_url + '?imported=' + Date.now();
            setTimeout(() => window.location.href = redirectUrl, 2000);
        } else {
            throw new Error(data.error || 'Import failed');
        }
    })
    .catch(error => {
        showErrorMessage('Import failed: ' + error.message);
    });
}
```

### 🐛 **Debugging Workflow:**

#### **When Validation Changes Don't Take Effect:**
```bash
# 1. Clear Python bytecode cache
Get-ChildItem -Recurse -Directory -Name "__pycache__" | ForEach-Object { Remove-Item $_ -Recurse -Force }

# 2. Restart Flask with cache bypass
taskkill /F /IM python.exe
python -B -m flask --app app.main run --debug --host=0.0.0.0 --port=5000
```

#### **Isolated Testing Pattern:**
```python
# ✅ CORRECT: Test validation changes in isolation
def test_na_validation():
    """Test that N/A validation works before running full Flask app."""
    test_data = {
        "Department": "ICU",
        "Name": "Test Equipment",
        "Installation_Date": "N/A",  # This should work
        "Warranty_End": "N/A",      # This should work
        # ... other required fields
    }
    
    try:
        entry = PPMImportEntry(**test_data)
        print("✅ SUCCESS: N/A validation working!")
        print(f"Installation_Date: {entry.Installation_Date}")
        print(f"Warranty_End: {entry.Warranty_End}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

if __name__ == "__main__":
    test_na_validation()
```

### 🎯 **UI/UX Integration Patterns:**

#### **Real-time Import Feedback:**
```javascript
// ✅ CORRECT: Show progress during import
function showImportProgress(dataType) {
    const progressDiv = document.createElement('div');
    progressDiv.className = 'alert alert-info import-feedback';
    progressDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="spinner-border spinner-border-sm me-2"></div>
            <div>
                <strong>Importing ${dataType.toUpperCase()} data...</strong><br>
                <small>Please wait while we process your file...</small>
            </div>
        </div>
    `;
    document.body.appendChild(progressDiv);
    return progressDiv;
}
```

#### **Record Counter Updates:**
```javascript
// ✅ CORRECT: Update counters after import
function updateRecordCounter() {
    const visibleRows = document.querySelectorAll('.equipment-table tbody tr:not([style*="display: none"])');
    const totalCount = visibleRows.length;
    const counterElement = document.getElementById('totalRecordsCount');
    
    if (counterElement) {
        counterElement.textContent = totalCount;
        // Add animation to indicate update
        counterElement.parentElement.classList.add('counter-update');
        setTimeout(() => {
            counterElement.parentElement.classList.remove('counter-update');
        }, 600);
    }
}

// Detect import completion and update counter
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('imported')) {
    updateRecordCounter();
    // Clean up URL
    window.history.replaceState(null, '', window.location.pathname);
}
```

### 🚨 **Common Pitfalls to Avoid:**

#### **Data Validation Mistakes:**
- ❌ **DON'T assume empty cells will be None** - they might be empty strings or "N/A"
- ❌ **DON'T rely only on frontend validation** - always validate on backend
- ❌ **DON'T skip testing after validation changes** - create isolated tests first
- ❌ **DON'T forget to handle both None and "N/A"** in transformation functions

#### **Import Service Mistakes:**
- ❌ **DON'T use generic error messages** - provide specific feedback about failures
- ❌ **DON'T ignore duplicate detection** - implement proper key-based checking
- ❌ **DON'T forget to backup data** before running transformation scripts
- ❌ **DON'T use pandas without dtype=str** for ID fields - prevents float conversion

#### **Debugging Mistakes:**
- ❌ **DON'T assume changes take effect immediately** - restart Flask for Python changes
- ❌ **DON'T skip cache clearing** when validation changes don't work
- ❌ **DON'T test only with synthetic data** - use actual problematic CSV files
- ❌ **DON'T forget to add debug logging** to trace validation execution

### 💡 **Success Patterns Summary:**

1. **Multi-layer Data Cleaning**: Clean at CSV processing, transformation, and validation layers
2. **Comprehensive N/A Handling**: Check for None, empty strings, AND "N/A" (case-insensitive)
3. **Isolated Testing**: Test validation changes outside Flask before full application testing
4. **Detailed Feedback**: Provide specific import results with counts and reasons for skips
5. **Cache Management**: Clear bytecode cache and restart Flask when Python changes don't take effect
6. **Real-time UI Updates**: Show progress during imports and update counters after completion

---

## 🔄 **CRITICAL: Test Email API Endpoint Configuration**

### ⚠️ **Missing Test Email API Endpoint Issue**

When test email functionality fails with 404 errors in the browser console, the issue is that JavaScript calls `/api/test-email` but this endpoint doesn't exist in the API routes.

#### **The Problem:**
```javascript
// ❌ JavaScript calls missing endpoint
fetch('/api/test-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
})
.then(response => response.json())
.catch(error => console.error('Test email failed:', error));
```

**Console Error:** `POST /api/test-email 404 (Not Found)`

#### **The Solution:**
Add the missing `/api/test-email` endpoint to `app/routes/api.py`:

```python
@api_bp.route('/test-email', methods=['POST'])
def send_test_email():
    """Send a test email to verify email configuration."""
    logger.info("Received request to send test email via API.")
    
    try:
        from app.services.email_service import EmailService
        
        # Load current settings
        settings = DataService.load_settings()
        recipient_email = settings.get('recipient_email', '')
        cc_emails = settings.get('cc_emails', '')
        
        # Enhanced configuration validation
        if not recipient_email:
            return jsonify({'error': 'No recipient email configured in settings.'}), 400
        
        # Check for Mailjet API credentials
        import os
        mailjet_api_key = os.getenv('MAILJET_API_KEY')
        mailjet_secret_key = os.getenv('MAILJET_SECRET_KEY')
        email_sender = os.getenv('EMAIL_SENDER')
        
        if not mailjet_api_key:
            return jsonify({'error': 'MAILJET_API_KEY environment variable is not configured.'}), 400
        
        if not mailjet_secret_key:
            return jsonify({'error': 'MAILJET_SECRET_KEY environment variable is not configured.'}), 400
            
        if not email_sender:
            return jsonify({'error': 'EMAIL_SENDER environment variable is not configured.'}), 400
        
        # Prepare test email content
        subject = "Hospital Equipment System - Test Email"
        body = f"""
        <h2>Test Email from Hospital Equipment System</h2>
        <p>This is a test email to verify your email configuration.</p>
        <p><strong>Sent to:</strong> {recipient_email}</p>
        {f'<p><strong>CC:</strong> {cc_emails}</p>' if cc_emails else ''}
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>If you received this email, your email configuration is working correctly!</p>
        """
        
        # Send test email
        email_service = EmailService()
        recipients = [recipient_email]
        if cc_emails:
            cc_list = [email.strip() for email in cc_emails.split(',') if email.strip()]
            recipients.extend(cc_list)
        
        success = email_service.send_immediate_email(recipients, subject, body)
        
        if success:
            logger.info(f"Test email sent successfully to {recipients}")
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {", ".join(recipients)}'
            })
        else:
            logger.error("Failed to send test email")
            return jsonify({'error': 'Failed to send test email. Please check your email configuration.'}), 500
            
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        return jsonify({'error': f'Failed to send test email: {str(e)}'}), 500
```

### 🎯 **Test Email Configuration Best Practices:**

#### **Environment Variables Setup:**
```bash
# Required environment variables for email functionality
MAILJET_API_KEY=your_mailjet_api_key_here
MAILJET_SECRET_KEY=your_mailjet_secret_key_here
EMAIL_SENDER=your-email@domain.com
```

#### **Enhanced Error Messages:**
The API endpoint provides specific error messages for each missing configuration:
- **Missing recipient email**: "No recipient email configured in settings."
- **Missing MAILJET_API_KEY**: "MAILJET_API_KEY environment variable is not configured."
- **Missing MAILJET_SECRET_KEY**: "MAILJET_SECRET_KEY environment variable is not configured."
- **Missing EMAIL_SENDER**: "EMAIL_SENDER environment variable is not configured."

#### **JavaScript Error Handling:**
```javascript
// ✅ CORRECT: Handle specific error messages
async function sendTestEmail() {
    try {
        const response = await fetch('/api/test-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccessToast(data.message);
        } else {
            showErrorToast(data.error || 'Failed to send test email');
        }
    } catch (error) {
        console.error('Test email error:', error);
        showErrorToast('Failed to send test email. Please try again.');
    }
}
```

### 🚨 **Common Test Email Issues:**

#### **Configuration Problems:**
- ❌ **Missing environment variables** - Mailjet credentials not set
- ❌ **Invalid email sender** - EMAIL_SENDER not configured or invalid
- ❌ **No recipient configured** - Settings page recipient email empty
- ❌ **Network issues** - Firewall blocking Mailjet API calls

#### **Debugging Steps:**
1. **Check environment variables** - Verify all required vars are set
2. **Validate settings** - Ensure recipient email is configured
3. **Test API endpoint directly** - Use curl or Postman to test
4. **Check logs** - Look for specific error messages in Flask logs
5. **Verify network connectivity** - Test Mailjet API access

### 🔧 **Flask Restart Requirements:**
**ALWAYS restart Flask application** after adding the new API endpoint:

```bash
# Stop Flask
taskkill /F /IM python.exe

# Restart Flask
python -B app/main.py
```

### 💡 **Success Indicators:**
- ✅ **No 404 errors** in browser console for `/api/test-email`
- ✅ **Specific error messages** help identify configuration issues
- ✅ **Test emails delivered** to configured recipients
- ✅ **Success toast notifications** confirm email sending
- ✅ **Proper logging** shows email sending status

---

## General Development Rules

### 🎯 **Code Quality Standards:**
- Follow PEP 8 Python style guidelines
- Use descriptive variable and function names
- Add comprehensive error handling
- Include logging for debugging
- Write self-documenting code with clear comments

### 🔒 **Security Practices:**
- Validate all user inputs
- Use parameterized queries for databases
- Keep sensitive data in environment variables
- Implement proper authentication and authorization

### 📝 **Documentation Standards:**
- Update README files when adding new features
- Document API endpoints and expected formats
- Comment complex business logic
- Maintain accurate requirements files

### 🧪 **Testing Protocol:**
- Test all changes in development environment first
- Verify both positive and negative test cases
- Check error handling and edge cases
- Ensure backward compatibility when possible

---

*Created to prevent repeating Flask restart, template cloning, and duplicate files mistakes.* 