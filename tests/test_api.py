import json
from unittest.mock import patch

# Helper function to create sample data (can be expanded or moved)
def create_sample_ppm_entry(SERIAL="PPM_API_S001", **override_kwargs):
    data = {
        "NO": 1, "EQUIPMENT": "PPM Test Device", "MODEL": "PPM-XYZ", "Name": "PPM Device XYZ",
        "SERIAL": SERIAL, "MANUFACTURER": "PPM Corp", "Department": "Test Dept",
        "LOG_NO": "LOG001", "Installation_Date": "01/01/2024", "Warranty_End": "01/01/2026",
        "Eng1": "E1", "Eng2": "", "Eng3": "", "Eng4": "",
        "Status": "Upcoming",
        "PPM_Q_I": {"engineer": "Q1 Eng"}, "PPM_Q_II": {"engineer": ""},
        "PPM_Q_III": {"engineer": ""}, "PPM_Q_IV": {"engineer": ""}
    }
    data.update(override_kwargs)
    return data

def create_sample_ocm_entry(SERIAL="OCM_API_S001", **override_kwargs):
    data = {
        "NO": 1, "EQUIPMENT": "OCM Test Device", "MODEL": "OCM-ABC", "Name": "OCM Device ABC",
        "SERIAL": SERIAL, "MANUFACTURER": "OCM Corp", "Department": "Test Dept OCM",
        "LOG_NO": "LOG002", "Installation_Date": "02/01/2024", "Warranty_End": "02/01/2026",
        "Service_Date": "01/03/2024", "Next_Maintenance": "01/09/2024", "ENGINEER": "OCM EngX",
        "Status": "Upcoming", "PPM": ""
    }
    data.update(override_kwargs)
    return data

# --- Tests for GET /equipment/<data_type> ---
def test_get_all_equipment_ppm_success(client):
    sample_ppm_list = [create_sample_ppm_entry("PPM01"), create_sample_ppm_entry("PPM02")]
    with patch('app.services.data_service.DataService.get_all_entries', return_value=sample_ppm_list) as mock_get_all:
        response = client.get('/api/equipment/ppm')
        assert response.status_code == 200
        json_data = response.get_json()
        assert len(json_data) == 2
        assert json_data[0]['SERIAL'] == "PPM01"
        mock_get_all.assert_called_once_with('ppm')

def test_get_all_equipment_ocm_success(client):
    sample_ocm_list = [create_sample_ocm_entry("OCM01")]
    with patch('app.services.data_service.DataService.get_all_entries', return_value=sample_ocm_list) as mock_get_all:
        response = client.get('/api/equipment/ocm')
        assert response.status_code == 200
        json_data = response.get_json()
        assert len(json_data) == 1
        assert json_data[0]['SERIAL'] == "OCM01"
        mock_get_all.assert_called_once_with('ocm')

def test_get_all_equipment_invalid_data_type(client):
    response = client.get('/api/equipment/invalid_type')
    assert response.status_code == 400
    json_data = response.get_json()
    assert "Invalid data type" in json_data['error']

# --- Tests for GET /equipment/<data_type>/<SERIAL> ---
def test_get_equipment_by_serial_ppm_success(client):
    sample_ppm = create_sample_ppm_entry("PPM_S001")
    with patch('app.services.data_service.DataService.get_entry', return_value=sample_ppm) as mock_get_one:
        response = client.get('/api/equipment/ppm/PPM_S001')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['SERIAL'] == "PPM_S001"
        assert json_data['MODEL'] == "PPM-XYZ"
        mock_get_one.assert_called_once_with('ppm', "PPM_S001")

def test_get_equipment_by_serial_ocm_success(client):
    sample_ocm = create_sample_ocm_entry("OCM_S001")
    with patch('app.services.data_service.DataService.get_entry', return_value=sample_ocm) as mock_get_one:
        response = client.get('/api/equipment/ocm/OCM_S001')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['SERIAL'] == "OCM_S001"
        mock_get_one.assert_called_once_with('ocm', "OCM_S001")

def test_get_equipment_by_serial_not_found(client):
    with patch('app.services.data_service.DataService.get_entry', return_value=None) as mock_get_one:
        response = client.get('/api/equipment/ppm/NONEXISTENT')
        assert response.status_code == 404
        json_data = response.get_json()
        assert "not found" in json_data['error']
        mock_get_one.assert_called_once_with('ppm', "NONEXISTENT")

def test_get_equipment_by_serial_invalid_data_type(client):
    response = client.get('/api/equipment/invalid_type/ANYSERIAL')
    assert response.status_code == 400
    json_data = response.get_json()
    assert "Invalid data type" in json_data['error']

# --- Tests for POST /equipment/<data_type> ---
def test_add_equipment_ppm_success(client):
    new_ppm_data_payload = {k: v for k, v in create_sample_ppm_entry("PPM_NEW01").items() if k != 'NO'} # NO is auto-assigned
    # For PPM_Q_X fields, payload should be dicts like {"engineer": "name"}
    # create_sample_ppm_entry already does this.

    # This is what DataService.add_entry is expected to return
    returned_ppm_from_service = create_sample_ppm_entry("PPM_NEW01", NO=10)

    with patch('app.services.data_service.DataService.add_entry', return_value=returned_ppm_from_service) as mock_add:
        response = client.post('/api/equipment/ppm', json=new_ppm_data_payload)
        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data['SERIAL'] == "PPM_NEW01"
        assert json_data['NO'] == 10 # Check if NO from service is in response
        mock_add.assert_called_once_with('ppm', new_ppm_data_payload)

def test_add_equipment_ocm_success(client):
    new_ocm_data_payload = {k: v for k, v in create_sample_ocm_entry("OCM_NEW01").items() if k != 'NO'}
    returned_ocm_from_service = create_sample_ocm_entry("OCM_NEW01", NO=11)

    with patch('app.services.data_service.DataService.add_entry', return_value=returned_ocm_from_service) as mock_add:
        response = client.post('/api/equipment/ocm', json=new_ocm_data_payload)
        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data['SERIAL'] == "OCM_NEW01"
        assert json_data['NO'] == 11
        mock_add.assert_called_once_with('ocm', new_ocm_data_payload)

def test_add_equipment_validation_error(client):
    new_ppm_data_payload = {"MODEL": "Incomplete"} # Missing required fields
    with patch('app.services.data_service.DataService.add_entry', side_effect=ValueError("Mocked Pydantic Validation Error: Field X required")) as mock_add:
        response = client.post('/api/equipment/ppm', json=new_ppm_data_payload)
        assert response.status_code == 400
        json_data = response.get_json()
        assert "Mocked Pydantic Validation Error" in json_data['error']
        mock_add.assert_called_once_with('ppm', new_ppm_data_payload)

def test_add_equipment_duplicate_serial(client):
    ppm_payload = {k: v for k,v in create_sample_ppm_entry("PPM_DUP01").items() if k != 'NO'}
    with patch('app.services.data_service.DataService.add_entry', side_effect=ValueError("Duplicate SERIAL detected")) as mock_add:
        response = client.post('/api/equipment/ppm', json=ppm_payload)
        assert response.status_code == 400
        json_data = response.get_json()
        assert "Duplicate SERIAL detected" in json_data['error']
        mock_add.assert_called_once_with('ppm', ppm_payload)

# --- Tests for PUT /equipment/<data_type>/<SERIAL> ---
def test_update_equipment_ppm_success(client):
    update_ppm_payload = create_sample_ppm_entry("PPM_UPD01", MODEL="PPM-XYZ-v2")
    # The payload for update includes all fields, including SERIAL matching the URL one.
    # NO might or might not be in payload, DataService.update_entry should handle it (preserves existing NO).

    # This is what DataService.update_entry is expected to return
    returned_ppm_from_service = create_sample_ppm_entry("PPM_UPD01", MODEL="PPM-XYZ-v2", NO=5)

    with patch('app.services.data_service.DataService.update_entry', return_value=returned_ppm_from_service) as mock_update:
        response = client.put('/api/equipment/ppm/PPM_UPD01', json=update_ppm_payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['MODEL'] == "PPM-XYZ-v2"
        assert json_data['SERIAL'] == "PPM_UPD01"
        assert json_data['NO'] == 5
        # DataService.update_entry expects the full data dict
        mock_update.assert_called_once_with('ppm', "PPM_UPD01", update_ppm_payload)

def test_update_equipment_ocm_success(client):
    update_ocm_payload = create_sample_ocm_entry("OCM_UPD01", MODEL="OCM-ABC-v2")
    returned_ocm_from_service = create_sample_ocm_entry("OCM_UPD01", MODEL="OCM-ABC-v2", NO=7)

    with patch('app.services.data_service.DataService.update_entry', return_value=returned_ocm_from_service) as mock_update:
        response = client.put('/api/equipment/ocm/OCM_UPD01', json=update_ocm_payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['MODEL'] == "OCM-ABC-v2"
        mock_update.assert_called_once_with('ocm', "OCM_UPD01", update_ocm_payload)

def test_update_equipment_SERIAL_mismatch(client):
    update_payload = create_sample_ppm_entry(SERIAL="PPM_WRONG_SERIAL")
    response = client.put('/api/equipment/ppm/PPM_ACTUAL_SERIAL', json=update_payload)
    assert response.status_code == 400
    json_data = response.get_json()
    assert "SERIAL in payload must match URL parameter" in json_data['error']

def test_update_equipment_not_found(client):
    update_payload = create_sample_ppm_entry("PPM_NOEXIST")
    with patch('app.services.data_service.DataService.update_entry', side_effect=KeyError("Entry not found")) as mock_update:
        response = client.put('/api/equipment/ppm/PPM_NOEXIST', json=update_payload)
        assert response.status_code == 404
        json_data = response.get_json()
        assert "not found" in json_data['error']
        mock_update.assert_called_once_with('ppm', "PPM_NOEXIST", update_payload)

def test_update_equipment_validation_error(client):
    update_payload = create_sample_ppm_entry("PPM_VALID_ERR")
    update_payload["Installation_Date"] = "bad-date" # Invalid data
    with patch('app.services.data_service.DataService.update_entry', side_effect=ValueError("Mocked Pydantic Validation Error")) as mock_update:
        response = client.put('/api/equipment/ppm/PPM_VALID_ERR', json=update_payload)
        assert response.status_code == 400
        json_data = response.get_json()
        assert "Mocked Pydantic Validation Error" in json_data['error']
        mock_update.assert_called_once_with('ppm', "PPM_VALID_ERR", update_payload)


# --- Tests for DELETE /equipment/<data_type>/<SERIAL> ---
def test_delete_equipment_ppm_success(client):
    with patch('app.services.data_service.DataService.delete_entry', return_value=True) as mock_delete:
        response = client.delete('/api/equipment/ppm/PPM_DEL01')
        assert response.status_code == 200
        json_data = response.get_json()
        assert "deleted successfully" in json_data['message']
        mock_delete.assert_called_once_with('ppm', "PPM_DEL01")

def test_delete_equipment_ocm_success(client):
    with patch('app.services.data_service.DataService.delete_entry', return_value=True) as mock_delete:
        response = client.delete('/api/equipment/ocm/OCM_DEL01')
        assert response.status_code == 200
        mock_delete.assert_called_once_with('ocm', "OCM_DEL01")

def test_delete_equipment_not_found(client):
    with patch('app.services.data_service.DataService.delete_entry', return_value=False) as mock_delete:
        response = client.delete('/api/equipment/ppm/PPM_NODEL01')
        assert response.status_code == 404
        json_data = response.get_json()
        assert "not found" in json_data['error']
        mock_delete.assert_called_once_with('ppm', "PPM_NODEL01")

import io # For simulating file uploads

# --- Tests for GET /export/<data_type> ---
def test_export_data_ppm_success(client):
    sample_csv_string = "NO,EQUIPMENT,MODEL,SERIAL\n1,Device1,ModelX,SN001"
    with patch('app.services.data_service.DataService.export_data', return_value=sample_csv_string) as mock_export:
        response = client.get('/api/export/ppm')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        assert "ppm_export" in response.headers["Content-Disposition"]
        assert response.data.decode('utf-8') == sample_csv_string
        mock_export.assert_called_once_with('ppm')

def test_export_data_ocm_success(client):
    sample_csv_string = "NO,EQUIPMENT,MODEL,SERIAL\n1,Device2,ModelY,SN002"
    with patch('app.services.data_service.DataService.export_data', return_value=sample_csv_string) as mock_export:
        response = client.get('/api/export/ocm')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert response.data.decode('utf-8') == sample_csv_string
        mock_export.assert_called_once_with('ocm')

def test_export_data_invalid_type(client):
    response = client.get('/api/export/wrongtype')
    assert response.status_code == 400
    assert "Invalid data type" in response.get_json()['error']


# --- Tests for POST /import/<data_type> ---
def test_import_data_ppm_success(client):
    mock_import_result = {"added_count": 1, "updated_count": 0, "skipped_count": 0, "errors": []}
    with patch('app.services.data_service.DataService.import_data', return_value=mock_import_result) as mock_import:
        # Simulate file upload
        csv_data = b"EQUIPMENT,MODEL,SERIAL\nDevice3,ModelZ,SN003" # Minimal valid CSV row
        data = {'file': (io.BytesIO(csv_data), 'test.csv')}
        response = client.post('/api/import/ppm', content_type='multipart/form-data', data=data)

        assert response.status_code == 200 # Or 207 if there are errors but some success
        json_data = response.get_json()
        assert json_data["added_count"] == 1
        mock_import.assert_called_once() # Check args if needed, esp. file_stream type

def test_import_data_ocm_partial_success_with_errors(client):
    mock_import_result = {"added_count": 0, "updated_count": 1, "skipped_count": 1, "errors": ["Row 2: Bad date format"]}
    with patch('app.services.data_service.DataService.import_data', return_value=mock_import_result) as mock_import:
        csv_data = b"EQUIPMENT,MODEL,SERIAL\nDevice4,ModelA,SN004\nDevice5,ModelB,SN005"
        data = {'file': (io.BytesIO(csv_data), 'test.csv')}
        response = client.post('/api/import/ocm', content_type='multipart/form-data', data=data)

        assert response.status_code == 207 # Multi-Status for partial success with errors
        json_data = response.get_json()
        assert json_data["updated_count"] == 1
        assert json_data["skipped_count"] == 1
        assert len(json_data["errors"]) == 1
        mock_import.assert_called_once()

def test_import_data_no_file(client):
    response = client.post('/api/import/ppm', content_type='multipart/form-data', data={})
    assert response.status_code == 400
    assert "No file part" in response.get_json()['error']

def test_import_data_wrong_file_type(client):
    data = {'file': (io.BytesIO(b"this is not a csv"), 'test.txt')}
    response = client.post('/api/import/ppm', content_type='multipart/form-data', data=data)
    assert response.status_code == 400
    assert "Invalid file type, only CSV allowed" in response.get_json()['error']

def test_import_data_service_failure(client):
    # Test when DataService.import_data itself raises an unexpected exception
    with patch('app.services.data_service.DataService.import_data', side_effect=Exception("Unexpected service error")) as mock_import:
        csv_data = b"EQUIPMENT,MODEL,SERIAL\nDeviceFail,ModelFail,SNFAIL"
        data = {'file': (io.BytesIO(csv_data), 'test.csv')}
        response = client.post('/api/import/ppm', content_type='multipart/form-data', data=data)
        assert response.status_code == 500
        json_data = response.get_json()
        assert "Failed to import ppm data" in json_data["error"]
        assert "Unexpected service error" in json_data["details"]


# --- Tests for POST /bulk_delete/<data_type> ---
def test_bulk_delete_success(client):
    serials_to_delete = ["SN001", "SN002", "SN003"]
    # Mock delete_entry to simulate behavior
    def mock_delete_side_effect(data_type, serial):
        if serial == "SN003": return False # Simulate one not found
        return True

    with patch('app.services.data_service.DataService.delete_entry', side_effect=mock_delete_side_effect) as mock_delete:
        response = client.post('/api/bulk_delete/ppm', json={"serials": serials_to_delete})
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["deleted_count"] == 2
        assert json_data["not_found"] == 1
        # Check DataService.delete_entry was called for each serial
        assert mock_delete.call_count == len(serials_to_delete)

def test_bulk_delete_no_serials_provided(client):
    response = client.post('/api/bulk_delete/ppm', json={"serials": []})
    assert response.status_code == 400
    json_data = response.get_json()
    assert "No serials provided" in json_data['message']

def test_bulk_delete_invalid_data_type(client):
    response = client.post('/api/bulk_delete/wrongtype', json={"serials": ["SN001"]})
    assert response.status_code == 400
    json_data = response.get_json()
    assert "Invalid data type" in json_data['message']


# --- Tests for /api/settings ---

def test_get_settings_success(client):
    """Test successfully retrieving settings."""
    # Mock DataService.load_settings
    mock_settings_data = {
        "email_notifications_enabled": True,
        "email_reminder_interval_minutes": 60,
        "recipient_email": "test@example.com",
        "push_notifications_enabled": False,
        "push_notification_interval_minutes": 30
    }
    with patch('app.services.data_service.DataService.load_settings', return_value=mock_settings_data) as mock_load:
        response = client.get('/api/settings')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data == mock_settings_data
        mock_load.assert_called_once()

def test_get_settings_load_error(client):
    """Test error handling when DataService.load_settings fails."""
    with patch('app.services.data_service.DataService.load_settings', side_effect=Exception("Failed to load")) as mock_load:
        response = client.get('/api/settings')
        assert response.status_code == 500
        json_data = response.get_json()
        assert "Failed to load settings" in json_data['error']
        mock_load.assert_called_once()

def test_save_settings_success(client):
    """Test successfully saving valid settings."""
    new_settings_payload = {
        "email_notifications_enabled": False,
        "email_reminder_interval_minutes": 120,
        "recipient_email": "new@example.com",
        "push_notifications_enabled": True,
        "push_notification_interval_minutes": 45
    }
    # Mock load_settings (called first in the endpoint) and save_settings
    # The endpoint loads current, updates, then saves.
    # So, save_settings will be called with the merged data.
    initial_settings_data = {
        "email_notifications_enabled": True, "email_reminder_interval_minutes": 60, "recipient_email": "old@example.com",
        "push_notifications_enabled": False, "push_notification_interval_minutes": 30,
        "another_existing_setting": "value" # To test preservation
    }

    expected_saved_settings = initial_settings_data.copy()
    expected_saved_settings.update(new_settings_payload)

    with patch('app.services.data_service.DataService.load_settings', return_value=initial_settings_data) as mock_load, \
         patch('app.services.data_service.DataService.save_settings', return_value=None) as mock_save:
        response = client.post('/api/settings', json=new_settings_payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert "Settings saved successfully" in json_data['message']
        assert json_data['settings'] == expected_saved_settings

        mock_load.assert_called_once()
        mock_save.assert_called_once_with(expected_saved_settings)


def test_save_settings_validation_errors(client):
    """Test validation errors when saving settings."""
    # Test invalid type for boolean
    invalid_payload_type = {"email_notifications_enabled": "not-a-boolean"}
    response = client.post('/api/settings', json=invalid_payload_type)
    assert response.status_code == 400
    assert "Invalid type for email_notifications_enabled" in response.get_json()['error']

    # Test invalid value for interval (e.g., zero or negative)
    valid_bools_invalid_interval = {
        "email_notifications_enabled": True, "email_reminder_interval_minutes": 0, "recipient_email": "test@example.com",
        "push_notifications_enabled": True, "push_notification_interval_minutes": 30
    }
    response = client.post('/api/settings', json=valid_bools_invalid_interval)
    assert response.status_code == 400
    assert "Invalid value for email_reminder_interval_minutes" in response.get_json()['error']

    valid_email_invalid_push_interval = {
        "email_notifications_enabled": True, "email_reminder_interval_minutes": 60, "recipient_email": "test@example.com",
        "push_notifications_enabled": True, "push_notification_interval_minutes": -5
    }
    response = client.post('/api/settings', json=valid_email_invalid_push_interval)
    assert response.status_code == 400
    assert "Invalid value for push_notification_interval_minutes" in response.get_json()['error']

    # Test missing key (e.g. push_notifications_enabled is required by the endpoint)
    missing_key_payload = {
        "email_notifications_enabled": False,
        "email_reminder_interval_minutes": 120,
        "recipient_email": "new@example.com",
        # "push_notifications_enabled": True, # Missing
        "push_notification_interval_minutes": 45
    }
    response = client.post('/api/settings', json=missing_key_payload)
    assert response.status_code == 400 # Should fail because push_notifications_enabled will be None, failing bool check
    assert "Invalid type for push_notifications_enabled" in response.get_json()['error']


def test_save_settings_save_error(client):
    """Test error handling when DataService.save_settings fails."""
    settings_payload = {
        "email_notifications_enabled": True, "email_reminder_interval_minutes": 60, "recipient_email": "test@example.com",
        "push_notifications_enabled": False, "push_notification_interval_minutes": 30
    }
    with patch('app.services.data_service.DataService.load_settings', return_value=settings_payload), \
         patch('app.services.data_service.DataService.save_settings', side_effect=Exception("Failed to save")) as mock_save:
        response = client.post('/api/settings', json=settings_payload)
        assert response.status_code == 500
        json_data = response.get_json()
        assert "Failed to save settings" in json_data['error']
        mock_save.assert_called_once()
