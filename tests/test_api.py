import json
from unittest.mock import patch

# Helper function to create sample data (can be expanded or moved)

from unittest.mock import patch # Ensure patch is imported if not already common
from app.services.training_service import TrainingService # For patching

def create_sample_training_record_payload(employee_id="TRN_API_E001", name="API Test User", **override_kwargs):
    data = {
        "employee_id": employee_id,
        "name": name,
        "department": "API Test Dept",
        "trainer": "API Test Trainer",
        "trained_machines": ["MachineAPI", "MachineTest"]
    }
    data.update(override_kwargs)
    return data

def create_sample_training_record_response_data(id=1, employee_id="TRN_API_E001", name="API Test User", **override_kwargs):
    data = {
        "id": id,
        "employee_id": employee_id,
        "name": name,
        "department": "API Test Dept",
        "trainer": "API Test Trainer",
        "trained_machines": ["MachineAPI", "MachineTest"]
    }
    data.update(override_kwargs)
    return data

def create_sample_ppm_entry(mfg_serial="PPM_API_S001", **override_kwargs):
    data = {
        "NO": 1, "EQUIPMENT": "PPM Test Device", "MODEL": "PPM-XYZ", "Name": "PPM Device XYZ",
        "MFG_SERIAL": mfg_serial, "MANUFACTURER": "PPM Corp", "Department": "Test Dept",
        "LOG_NO": "LOG001", "Installation_Date": "01/01/2024", "Warranty_End": "01/01/2026",
        "Eng1": "E1", "Eng2": "", "Eng3": "", "Eng4": "",
        "Status": "Upcoming",
        "PPM_Q_I": {"engineer": "Q1 Eng"}, "PPM_Q_II": {"engineer": ""},
        "PPM_Q_III": {"engineer": ""}, "PPM_Q_IV": {"engineer": ""}
    }
    data.update(override_kwargs)
    return data

def create_sample_ocm_entry(mfg_serial="OCM_API_S001", **override_kwargs):
    data = {
        "NO": 1, "EQUIPMENT": "OCM Test Device", "MODEL": "OCM-ABC", "Name": "OCM Device ABC",
        "MFG_SERIAL": mfg_serial, "MANUFACTURER": "OCM Corp", "Department": "Test Dept OCM",
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
        assert json_data[0]['MFG_SERIAL'] == "PPM01"
        mock_get_all.assert_called_once_with('ppm')

def test_get_all_equipment_ocm_success(client):
    sample_ocm_list = [create_sample_ocm_entry("OCM01")]
    with patch('app.services.data_service.DataService.get_all_entries', return_value=sample_ocm_list) as mock_get_all:
        response = client.get('/api/equipment/ocm')
        assert response.status_code == 200
        json_data = response.get_json()
        assert len(json_data) == 1
        assert json_data[0]['MFG_SERIAL'] == "OCM01"
        mock_get_all.assert_called_once_with('ocm')

def test_get_all_equipment_invalid_data_type(client):
    response = client.get('/api/equipment/invalid_type')
    assert response.status_code == 400
    json_data = response.get_json()
    assert "Invalid data type" in json_data['error']

# --- Tests for GET /equipment/<data_type>/<mfg_serial> ---
def test_get_equipment_by_serial_ppm_success(client):
    sample_ppm = create_sample_ppm_entry("PPM_S001")
    with patch('app.services.data_service.DataService.get_entry', return_value=sample_ppm) as mock_get_one:
        response = client.get('/api/equipment/ppm/PPM_S001')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['MFG_SERIAL'] == "PPM_S001"
        assert json_data['MODEL'] == "PPM-XYZ"
        mock_get_one.assert_called_once_with('ppm', "PPM_S001")

def test_get_equipment_by_serial_ocm_success(client):
    sample_ocm = create_sample_ocm_entry("OCM_S001")
    with patch('app.services.data_service.DataService.get_entry', return_value=sample_ocm) as mock_get_one:
        response = client.get('/api/equipment/ocm/OCM_S001')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['MFG_SERIAL'] == "OCM_S001"
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
        assert json_data['MFG_SERIAL'] == "PPM_NEW01"
        assert json_data['NO'] == 10 # Check if NO from service is in response
        mock_add.assert_called_once_with('ppm', new_ppm_data_payload)

def test_add_equipment_ocm_success(client):
    new_ocm_data_payload = {k: v for k, v in create_sample_ocm_entry("OCM_NEW01").items() if k != 'NO'}
    returned_ocm_from_service = create_sample_ocm_entry("OCM_NEW01", NO=11)

    with patch('app.services.data_service.DataService.add_entry', return_value=returned_ocm_from_service) as mock_add:
        response = client.post('/api/equipment/ocm', json=new_ocm_data_payload)
        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data['MFG_SERIAL'] == "OCM_NEW01"
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
    with patch('app.services.data_service.DataService.add_entry', side_effect=ValueError("Duplicate MFG_SERIAL detected")) as mock_add:
        response = client.post('/api/equipment/ppm', json=ppm_payload)
        assert response.status_code == 400
        json_data = response.get_json()
        assert "Duplicate MFG_SERIAL detected" in json_data['error']
        mock_add.assert_called_once_with('ppm', ppm_payload)

# --- Tests for PUT /equipment/<data_type>/<mfg_serial> ---
def test_update_equipment_ppm_success(client):
    update_ppm_payload = create_sample_ppm_entry("PPM_UPD01", MODEL="PPM-XYZ-v2")
    # The payload for update includes all fields, including MFG_SERIAL matching the URL one.
    # NO might or might not be in payload, DataService.update_entry should handle it (preserves existing NO).

    # This is what DataService.update_entry is expected to return
    returned_ppm_from_service = create_sample_ppm_entry("PPM_UPD01", MODEL="PPM-XYZ-v2", NO=5)

    with patch('app.services.data_service.DataService.update_entry', return_value=returned_ppm_from_service) as mock_update:
        response = client.put('/api/equipment/ppm/PPM_UPD01', json=update_ppm_payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['MODEL'] == "PPM-XYZ-v2"
        assert json_data['MFG_SERIAL'] == "PPM_UPD01"
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

def test_update_equipment_mfg_serial_mismatch(client):
    update_payload = create_sample_ppm_entry(MFG_SERIAL="PPM_WRONG_SERIAL")
    response = client.put('/api/equipment/ppm/PPM_ACTUAL_SERIAL', json=update_payload)
    assert response.status_code == 400
    json_data = response.get_json()
    assert "MFG_SERIAL in payload must match URL parameter" in json_data['error']

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


# --- Tests for DELETE /equipment/<data_type>/<mfg_serial> ---
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
    sample_csv_string = "NO,EQUIPMENT,MODEL,MFG_SERIAL\n1,Device1,ModelX,SN001"
    with patch('app.services.data_service.DataService.export_data', return_value=sample_csv_string) as mock_export:
        response = client.get('/api/export/ppm')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        assert "ppm_export" in response.headers["Content-Disposition"]
        assert response.data.decode('utf-8') == sample_csv_string
        mock_export.assert_called_once_with('ppm')

def test_export_data_ocm_success(client):
    sample_csv_string = "NO,EQUIPMENT,MODEL,MFG_SERIAL\n1,Device2,ModelY,SN002"
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
        csv_data = b"EQUIPMENT,MODEL,MFG_SERIAL\nDevice3,ModelZ,SN003" # Minimal valid CSV row
        data = {'file': (io.BytesIO(csv_data), 'test.csv')}
        response = client.post('/api/import/ppm', content_type='multipart/form-data', data=data)

        assert response.status_code == 200 # Or 207 if there are errors but some success
        json_data = response.get_json()
        assert json_data["added_count"] == 1
        mock_import.assert_called_once() # Check args if needed, esp. file_stream type

def test_import_data_ocm_partial_success_with_errors(client):
    mock_import_result = {"added_count": 0, "updated_count": 1, "skipped_count": 1, "errors": ["Row 2: Bad date format"]}
    with patch('app.services.data_service.DataService.import_data', return_value=mock_import_result) as mock_import:
        csv_data = b"EQUIPMENT,MODEL,MFG_SERIAL\nDevice4,ModelA,SN004\nDevice5,ModelB,SN005"
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
        csv_data = b"EQUIPMENT,MODEL,MFG_SERIAL\nDeviceFail,ModelFail,SNFAIL"
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

# --- Tests for Training API (/api/training) ---

# POST /api/training
def test_create_training_record_api_success(client): # client fixture from conftest.py
    payload = create_sample_training_record_payload()
    service_response = create_sample_training_record_response_data(id=1, **payload)

    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        # Mock the instance and its method
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.create_training_record.return_value = service_response

        response = client.post('/api/training', json=payload)

        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data["id"] == 1
        assert json_data["employee_id"] == payload["employee_id"]
        mock_service_instance.create_training_record.assert_called_once_with(payload)

def test_create_training_record_api_validation_error(client):
    payload = {"name": "Only Name"} # Missing employee_id
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.create_training_record.side_effect = ValueError("Employee ID is required")

        response = client.post('/api/training', json=payload)

        assert response.status_code == 400
        json_data = response.get_json()
        assert "Employee ID is required" in json_data['error']
        mock_service_instance.create_training_record.assert_called_once_with(payload)

def test_create_training_record_api_bad_request_no_json(client):
    response = client.post('/api/training', data="not json") # Sending raw data, not json
    assert response.status_code == 400 # Flask typically returns 400 if request.is_json is false
    json_response = response.get_json()
    assert json_response is not None
    assert "Request must be JSON" in json_response.get('error', '')


def test_create_training_record_api_service_exception(client):
    payload = create_sample_training_record_payload()
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.create_training_record.side_effect = Exception("Service unavailable")

        response = client.post('/api/training', json=payload)

        assert response.status_code == 500
        assert "Failed to create training record" in response.get_json()['error']
        mock_service_instance.create_training_record.assert_called_once_with(payload)


# GET /api/training
def test_get_all_training_records_api_success(client):
    records_data = [
        create_sample_training_record_response_data(id=1, employee_id="E01"),
        create_sample_training_record_response_data(id=2, employee_id="E02")
    ]
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.get_all_training_records.return_value = records_data

        response = client.get('/api/training') # Assuming /api/training is correct from Flask blueprint

        assert response.status_code == 200
        json_data = response.get_json()
        assert len(json_data) == 2
        assert json_data[0]["employee_id"] == "E01"
        mock_service_instance.get_all_training_records.assert_called_once_with(skip=0, limit=0) # Check default args

def test_get_all_training_records_api_with_pagination(client):
    records_data = [create_sample_training_record_response_data(id=1)]
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.get_all_training_records.return_value = records_data

        response = client.get('/api/training?skip=5&limit=10')
        assert response.status_code == 200
        mock_service_instance.get_all_training_records.assert_called_once_with(skip=5, limit=10)


def test_get_all_training_records_api_empty(client):
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.get_all_training_records.return_value = []

        response = client.get('/api/training')

        assert response.status_code == 200
        assert response.get_json() == []
        mock_service_instance.get_all_training_records.assert_called_once_with(skip=0, limit=0)

def test_get_all_training_records_api_service_exception(client):
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.get_all_training_records.side_effect = Exception("DB error")

        response = client.get('/api/training')

        assert response.status_code == 500
        assert "Failed to retrieve training records" in response.get_json()['error']
        mock_service_instance.get_all_training_records.assert_called_once_with(skip=0, limit=0)

# GET /api/training/<record_id>
def test_get_training_record_by_id_api_success(client):
    record_data = create_sample_training_record_response_data(id=123)
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.get_training_record.return_value = record_data

        response = client.get('/api/training/123')

        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["id"] == 123
        mock_service_instance.get_training_record.assert_called_once_with(123)

def test_get_training_record_by_id_api_not_found(client):
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.get_training_record.return_value = None

        response = client.get('/api/training/404')

        assert response.status_code == 404
        assert "Training record not found" in response.get_json()['error']
        mock_service_instance.get_training_record.assert_called_once_with(404)

def test_get_training_record_by_id_api_service_exception(client):
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.get_training_record.side_effect = Exception("Service error")

        response = client.get('/api/training/789')

        assert response.status_code == 500
        assert "Failed to retrieve training record" in response.get_json()['error']
        mock_service_instance.get_training_record.assert_called_once_with(789)

# PUT /api/training/<record_id>
def test_update_training_record_api_success(client):
    record_id = 456
    payload = create_sample_training_record_payload(name="Updated Name")
    service_response = create_sample_training_record_response_data(id=record_id, **payload)

    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.update_training_record.return_value = service_response

        response = client.put(f'/api/training/{record_id}', json=payload)

        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["name"] == "Updated Name"
        assert json_data["id"] == record_id
        mock_service_instance.update_training_record.assert_called_once_with(record_id, payload)

def test_update_training_record_api_not_found(client):
    record_id = 4041
    payload = create_sample_training_record_payload()
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.update_training_record.return_value = None

        response = client.put(f'/api/training/{record_id}', json=payload)

        assert response.status_code == 404
        assert "Training record not found" in response.get_json()['error'] # Updated message from route
        mock_service_instance.update_training_record.assert_called_once_with(record_id, payload)

def test_update_training_record_api_validation_error(client):
    record_id = 789
    payload = create_sample_training_record_payload(name="") # Empty name
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.update_training_record.side_effect = ValueError("Name cannot be empty")

        response = client.put(f'/api/training/{record_id}', json=payload)

        assert response.status_code == 400
        assert "Name cannot be empty" in response.get_json()['error']
        mock_service_instance.update_training_record.assert_called_once_with(record_id, payload)

def test_update_training_record_api_service_exception(client):
    record_id = 101
    payload = create_sample_training_record_payload()
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.update_training_record.side_effect = Exception("DB down")

        response = client.put(f'/api/training/{record_id}', json=payload)

        assert response.status_code == 500
        assert "Failed to update training record" in response.get_json()['error']
        mock_service_instance.update_training_record.assert_called_once_with(record_id, payload)


# DELETE /api/training/<record_id>
def test_delete_training_record_api_success(client):
    record_id = 777
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.delete_training_record.return_value = True

        response = client.delete(f'/api/training/{record_id}')

        assert response.status_code == 200
        assert "Training record deleted successfully" in response.get_json()['message']
        mock_service_instance.delete_training_record.assert_called_once_with(record_id)

def test_delete_training_record_api_not_found(client):
    record_id = 4042
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.delete_training_record.return_value = False

        response = client.delete(f'/api/training/{record_id}')

        assert response.status_code == 404
        assert "Training record not found" in response.get_json()['error']
        mock_service_instance.delete_training_record.assert_called_once_with(record_id)

def test_delete_training_record_api_service_exception(client):
    record_id = 888
    with patch('app.routes.api.TrainingService') as mock_training_service_class:
        mock_service_instance = mock_training_service_class.return_value
        mock_service_instance.delete_training_record.side_effect = Exception("Lock error")

        response = client.delete(f'/api/training/{record_id}')

        assert response.status_code == 500
        assert "Failed to delete training record" in response.get_json()['error']
        mock_service_instance.delete_training_record.assert_called_once_with(record_id)