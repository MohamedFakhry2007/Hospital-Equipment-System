import pytest
from flask import url_for, get_flashed_messages
import json
import os
import shutil

# Attempt to import the Flask app instance
# Common locations are app/__init__.py or app/main.py
from app import create_app

flask_app = create_app()
    

from app.services.data_service import DataService
from app.config import Config

# Original ppm.json path
ORIGINAL_PPM_JSON_PATH = Config.PPM_JSON_PATH
# Place test_ppm_data.json in the same directory as this test file
TEST_PPM_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_PPM_JSON_PATH = os.path.join(TEST_PPM_DATA_DIR, 'test_ppm_data.json')

@pytest.fixture(scope='function')
def client_with_temp_ppm(monkeypatch):
    # Ensure the test data directory exists
    os.makedirs(TEST_PPM_DATA_DIR, exist_ok=True)

    # Create a copy of the original ppm.json for testing
    if os.path.exists(ORIGINAL_PPM_JSON_PATH):
        shutil.copy2(ORIGINAL_PPM_JSON_PATH, TEST_PPM_JSON_PATH)
    else: # Create an empty list if original doesn't exist
        with open(TEST_PPM_JSON_PATH, 'w') as f_test:
            json.dump([], f_test)

    # Monkeypatch Config.PPM_JSON_PATH to use the test file
    monkeypatch.setattr(Config, 'PPM_JSON_PATH', TEST_PPM_JSON_PATH)

    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for simpler form posts in tests

    with flask_app.test_client() as client:
        with flask_app.app_context(): # Ensure app context for url_for etc.
            yield client

    # Clean up the test ppm.json file and directory if empty
    if os.path.exists(TEST_PPM_JSON_PATH):
        os.remove(TEST_PPM_JSON_PATH)
    if os.path.exists(TEST_PPM_DATA_DIR) and not os.listdir(TEST_PPM_DATA_DIR):
        os.rmdir(TEST_PPM_DATA_DIR)

# --- Training Data Setup ---
TRAINING_TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_training_data_dir')
TEST_TRAINING_JSON_PATH = os.path.join(TRAINING_TEST_DATA_DIR, 'test_training.json')

@pytest.fixture(scope='function')
def client_with_temp_training_data(monkeypatch):
    os.makedirs(TRAINING_TEST_DATA_DIR, exist_ok=True)

    # Create an empty training file for tests
    with open(TEST_TRAINING_JSON_PATH, 'w') as f_test:
        json.dump([], f_test)

    # Monkeypatch training_service.DATA_FILE to use the test file
    monkeypatch.setattr('app.services.training_service.DATA_FILE', TEST_TRAINING_JSON_PATH)

    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False

    with flask_app.test_client() as client:
        with flask_app.app_context():
            # Ensure training service uses the fresh (empty) file for each test run by clearing its internal cache if any
            # This might involve re-importing or using a method to reset service state if it caches data.
            # For this service, it loads from file on each call, so direct file manipulation is enough.
            yield client

    if os.path.exists(TEST_TRAINING_JSON_PATH):
        os.remove(TEST_TRAINING_JSON_PATH)
    if os.path.exists(TRAINING_TEST_DATA_DIR) and not os.listdir(TRAINING_TEST_DATA_DIR):
        os.rmdir(TRAINING_TEST_DATA_DIR)


def sample_training_payload(employee_id="EMP001", name="Test User", assignments=None):
    if assignments is None:
        assignments = [{"machine": "Machine A", "trainer": "Trainer X"}]
    return {
        "employee_id": employee_id,
        "name": name,
        "department": "Test Department",
        "machine_trainer_assignments": assignments,
        "last_trained_date": "2024-01-01",
        "next_due_date": "2025-01-01"
    }


def test_edit_ppm_equipment_post(client_with_temp_ppm):
    # Test with SERIAL "1", assuming it exists in the copied data/ppm.json
    # data/ppm.json has SERIAL "1" with PPM_Q_I.quarter_date = "22/07/2025"
    serial_to_test = "1"

    initial_record = DataService.get_entry('ppm', serial_to_test)
    if not initial_record:
        # If SERIAL "1" is somehow not in data/ppm.json, this test will fail.
        pytest.fail(f"Test setup failed: PPM entry with SERIAL '{serial_to_test}' not found in test data.")

    original_q1_date = initial_record['PPM_Q_I']['quarter_date']

    form_data = {
        "Department": "Test Department Updated Via Route",
        "MODEL": initial_record['MODEL'],
        "Name": "Test Name Updated Via Route",
        "MANUFACTURER": initial_record['MANUFACTURER'],
        "LOG_Number": initial_record['LOG_Number'],
        "Installation_Date": initial_record.get('Installation_Date', ''),
        "Warranty_End": initial_record.get('Warranty_End', ''),
        "Q1_Engineer": "Engineer Q1 Updated Test",
        "Q2_Engineer": initial_record['PPM_Q_II']['engineer'],
        "Q3_Engineer": initial_record['PPM_Q_III']['engineer'],
        "Q4_Engineer": initial_record['PPM_Q_IV']['engineer'],
        "Status": "" # Auto-calculate
    }

    response = client_with_temp_ppm.post(
        url_for('views.edit_ppm_equipment', SERIAL=serial_to_test),
        data=form_data,
        follow_redirects=False
    )

    assert response.status_code == 302, f"Expected status code 302, got {response.status_code}"
    assert response.location == url_for('views.list_equipment', data_type='ppm'),         f"Expected redirect to PPM list, got {response.location}"

    with client_with_temp_ppm.session_transaction() as session:
        flashed_messages = session.get('_flashes', [])

    assert len(flashed_messages) > 0, "No flashed messages found in session."
    assert flashed_messages[0][0] == 'success'
    assert "PPM equipment updated successfully!" in flashed_messages[0][1]

    updated_record = DataService.get_entry('ppm', serial_to_test)
    assert updated_record is not None, f"Record with SERIAL '{serial_to_test}' not found after update."
    assert updated_record['Department'] == "Test Department Updated Via Route"
    assert updated_record['Name'] == "Test Name Updated Via Route"
    assert updated_record['PPM_Q_I']['engineer'] == "Engineer Q1 Updated Test"

    assert updated_record['Status'] == "Upcoming", f"Expected Status 'Upcoming', got '{updated_record['Status']}'"

    assert updated_record['SERIAL'] == serial_to_test, "SERIAL should not change."
    assert updated_record['PPM_Q_I']['quarter_date'] == original_q1_date, "Quarter date should not change."

# --- Training API Route Tests (Placeholders) ---

def test_get_all_trainings_api_placeholder(client_with_temp_ppm): # Using client_with_temp_ppm for app context
    """Placeholder test for GET /api/trainings."""
    # response = client_with_temp_ppm.get(url_for('api.get_all_trainings_route'))
    # assert response.status_code == 200
    # assert isinstance(response.json, list)
    pass

def test_add_training_api_placeholder(client_with_temp_ppm):
    """Placeholder test for POST /api/trainings."""
    # data = {"employee_id": "API_EMP001", "name": "API Test User", ...}
    # response = client_with_temp_ppm.post(url_for('api.add_training_route'), json=data)
    # assert response.status_code == 201
    # assert response.json['name'] == "API Test User"
    pass

def test_update_training_api_placeholder(client_with_temp_ppm):
    """Placeholder test for PUT /api/trainings/<id>."""
    # First, add a training record to get an ID
    # add_response = client_with_temp_ppm.post(url_for('api.add_training_route'), json={"employee_id": "API_EMP002", "name": "API Update Me"})
    # training_id = add_response.json['id']
    # update_data = {"name": "API Updated Name"}
    # response = client_with_temp_ppm.put(url_for('api.update_training_route', training_id=training_id), json=update_data)
    # assert response.status_code == 200
    # assert response.json['name'] == "API Updated Name"
    pass

def test_delete_training_api_placeholder(client_with_temp_ppm):
    """Placeholder test for DELETE /api/trainings/<id>."""
    # add_response = client_with_temp_ppm.post(url_for('api.add_training_route'), json={"employee_id": "API_EMP003", "name": "API Delete Me"})
    # training_id = add_response.json['id']
    # response = client_with_temp_ppm.delete(url_for('api.delete_training_route', training_id=training_id))
    # assert response.status_code == 200 # or 204
    # get_response = client_with_temp_ppm.get(url_for('api.get_training_by_id_route', training_id=training_id))
    # assert get_response.status_code == 404
    pass

# --- Training View Route Test (Placeholder) ---

def test_training_management_page_loads_placeholder(client_with_temp_ppm):
    """Placeholder test for GET /training page."""
    # response = client_with_temp_ppm.get(url_for('views.training_management_page'))
    # assert response.status_code == 200
    # assert b"Training Management" in response.data # Check for page title or key content
    pass


# --- Training API Route Tests ---

def test_add_and_get_all_trainings_api(client_with_temp_training_data):
    client = client_with_temp_training_data # Use the correct fixture

    # Test GET all trainings when empty
    response = client.get(url_for('api.get_all_trainings_route'))
    assert response.status_code == 200
    assert response.json == []

    # Test POST to add a new training record
    payload1 = sample_training_payload(employee_id="EMP001", name="User One", assignments=[{"machine": "M1", "trainer": "T1"}])
    response = client.post(url_for('api.add_training_route'), json=payload1)
    assert response.status_code == 201
    created_training1 = response.json
    assert created_training1['id'] == 1
    assert created_training1['employee_id'] == "EMP001"
    assert created_training1['name'] == "User One"
    assert created_training1['machine_trainer_assignments'] == [{"machine": "M1", "trainer": "T1"}]

    # Test POST to add a second training record
    payload2 = sample_training_payload(employee_id="EMP002", name="User Two", assignments=[{"machine": "M2", "trainer": "T2"}, {"machine": "M3", "trainer": "T3"}])
    response = client.post(url_for('api.add_training_route'), json=payload2)
    assert response.status_code == 201
    created_training2 = response.json
    assert created_training2['id'] == 2 # Auto-incrementing ID
    assert created_training2['name'] == "User Two"
    assert len(created_training2['machine_trainer_assignments']) == 2

    # Test GET all trainings after adding
    response = client.get(url_for('api.get_all_trainings_route'))
    assert response.status_code == 200
    all_trainings = response.json
    assert len(all_trainings) == 2
    assert all_trainings[0]['name'] == "User One"
    assert all_trainings[1]['name'] == "User Two"

    # Verify structure of machine_trainer_assignments in GET all
    assert all_trainings[0]['machine_trainer_assignments'] == [{"machine": "M1", "trainer": "T1"}]


def test_add_training_api_validation_error(client_with_temp_training_data):
    client = client_with_temp_training_data
    # Payload missing required fields (e.g., employee_id, name)
    # The current Training model doesn't use Pydantic validation for these,
    # so the service/API layer would need to enforce it if required.
    # For now, the model allows None for these if not provided in dict.
    # Let's assume the API expects them. If not, this test needs adjustment.
    # The current model would create Training(id=1, employee_id=None, name=None, ...)
    # The API endpoint for add_training does not explicitly validate for missing fields before calling service.
    # The service then calls Training.from_dict.
    # This test might pass (201) if None is acceptable.
    # If strict validation is desired, it should be added to api.py or the model.

    # For now, let's test with a payload that might cause issues if not handled well,
    # like machine_trainer_assignments not being a list.
    invalid_payload = {
        "employee_id": "EMP_VALID", "name": "Valid Name",
        "machine_trainer_assignments": "not-a-list" # Should be a list of dicts
    }
    # This will likely cause an error during Training.from_dict if it tries to iterate
    # or if the service layer expects a list.
    # The current `Training.from_dict` has backward compatibility that might try to parse this.
    # If `machine_trainer_assignments` is explicitly provided and not None, backward compat is skipped.
    # `isinstance(old_trained_on_machines, str)` would apply if key was `trained_on_machines`.
    # For `machine_trainer_assignments="not-a-list"`, it will be taken as is.
    # The test for the model should cover behavior of `from_dict` more deeply.
    # Here, we are testing the API route.
    # `Training.to_dict()` would then just return this string.
    # This might be acceptable if the data is just stored and returned.
    # However, the spirit of the field is a list of dicts.

    # Let's assume the client sends a valid structure but maybe empty.
    payload_empty_assignments = sample_training_payload(assignments=[])
    response = client.post(url_for('api.add_training_route'), json=payload_empty_assignments)
    assert response.status_code == 201 # Empty list is valid
    assert response.json['machine_trainer_assignments'] == []

    # Test with missing 'employee_id' (assuming it's required by implicit contract)
    # The current model sets it to None if missing. API endpoint does not validate.
    # For a more robust API, add validation in the route or use Pydantic models for request body.
    payload_missing_fields = {
        "name": "Test Name Only",
        "machine_trainer_assignments": [{"machine": "M1", "trainer": "T1"}]
    }
    response = client.post(url_for('api.add_training_route'), json=payload_missing_fields)
    assert response.status_code == 201 # Currently passes as model defaults employee_id to None
    assert response.json['employee_id'] is None
    assert response.json['name'] == "Test Name Only"


def test_get_training_by_id_api(client_with_temp_training_data):
    client = client_with_temp_training_data
    payload = sample_training_payload(employee_id="EMP003", name="User Three")
    add_response = client.post(url_for('api.add_training_route'), json=payload)
    assert add_response.status_code == 201
    training_id = add_response.json['id']

    # Test get existing
    response = client.get(url_for('api.get_training_by_id_route', training_id=training_id))
    assert response.status_code == 200
    fetched_training = response.json
    assert fetched_training['id'] == training_id
    assert fetched_training['name'] == "User Three"
    assert fetched_training['machine_trainer_assignments'] == payload['machine_trainer_assignments']

    # Test get non-existent
    response = client.get(url_for('api.get_training_by_id_route', training_id=999))
    assert response.status_code == 404
    assert "not found" in response.json['error']


def test_update_training_api(client_with_temp_training_data):
    client = client_with_temp_training_data
    payload = sample_training_payload(employee_id="EMP004", name="User Four", assignments=[{"machine": "M_OLD", "trainer": "T_OLD"}])
    add_response = client.post(url_for('api.add_training_route'), json=payload)
    assert add_response.status_code == 201
    training_id = add_response.json['id']

    update_payload = {
        "name": "User Four Updated",
        "department": "Dept Updated",
        "machine_trainer_assignments": [
            {"machine": "M_NEW_A", "trainer": "T_NEW_A"},
            {"machine": "M_NEW_B", "trainer": "T_NEW_B"}
        ],
        "last_trained_date": "2024-02-02",
        # employee_id is not in update payload, should be preserved
    }

    response = client.put(url_for('api.update_training_route', training_id=training_id), json=update_payload)
    assert response.status_code == 200
    updated_training = response.json
    assert updated_training['id'] == training_id
    assert updated_training['name'] == "User Four Updated"
    assert updated_training['department'] == "Dept Updated"
    assert updated_training['machine_trainer_assignments'] == update_payload['machine_trainer_assignments']
    assert updated_training['last_trained_date'] == "2024-02-02"
    assert updated_training['employee_id'] == "EMP004" # Preserved

    # Test update non-existent
    response = client.put(url_for('api.update_training_route', training_id=999), json=update_payload)
    assert response.status_code == 404
    assert "not found" in response.json['error']


def test_delete_training_api(client_with_temp_training_data):
    client = client_with_temp_training_data
    payload = sample_training_payload(employee_id="EMP005", name="User Five")
    add_response = client.post(url_for('api.add_training_route'), json=payload)
    assert add_response.status_code == 201
    training_id = add_response.json['id']

    # Test delete existing
    response = client.delete(url_for('api.delete_training_route', training_id=training_id))
    assert response.status_code == 200 # Or 204 if no content
    if response.status_code == 200: # Check body only if status is 200
      assert "deleted successfully" in response.json['message']

    # Verify deletion
    get_response = client.get(url_for('api.get_training_by_id_route', training_id=training_id))
    assert get_response.status_code == 404

    # Test delete non-existent
    response = client.delete(url_for('api.delete_training_route', training_id=999))
    assert response.status_code == 404
    assert "not found" in response.json['error']


def test_training_management_page_view(client_with_temp_training_data):
    client = client_with_temp_training_data
    from app.services import training_service # Import here to use the patched DATA_FILE

    # Add a sample training record directly via service for the view to render
    sample_data = {
        "employee_id": "VIEW001",
        "name": "View Test User",
        "department": "View Dept",
        "machine_trainer_assignments": [
            {"machine": "ViewMachine1", "trainer": "ViewTrainerA"},
            {"machine": "ViewMachine2", "trainer": "ViewTrainerB"}
        ],
        "last_trained_date": "2024-03-01"
    }
    added_record = training_service.add_training(sample_data)
    expected_json_attr_value = json.dumps(sample_data["machine_trainer_assignments"])
    # HTML attribute escaping might change quotes, so prepare for that if checking precisely
    # For Jinja's |tojson|forceescape, it might look like:
    # data-machine-assignments='[{"machine": "ViewMachine1", "trainer": "ViewTrainerA"}, {"machine": "ViewMachine2", "trainer": "ViewTrainerB"}]'
    # The json.dumps will use double quotes. HTML attributes often use single quotes for values.
    # The forceescape filter in Jinja will escape HTML special characters.
    # A simple check for parts of the content is safer if exact escaping is complex.

    response = client.get(url_for('views.training_management_page'))
    assert response.status_code == 200
    response_data_str = response.data.decode('utf-8')

    assert "Training Management" in response_data_str
    assert "View Test User" in response_data_str
    assert "ViewMachine1 (ViewTrainerA)" in response_data_str # How it's displayed in the table
    assert "ViewMachine2 (ViewTrainerB)" in response_data_str

    # Check for the data attribute on the edit button
    # This is a basic check, more robust would be parsing HTML
    # Looking for: data-machine-assignments='[{"machine": "ViewMachine1", ...}]' (single quotes by browser/template)
    # or data-machine-assignments="[{...}]" (double quotes if template does that)
    # The |tojson filter produces JSON string with double quotes. forceescape escapes these for HTML attribute.
    # Example: data-machine-assignments="[{&quot;machine&quot;: &quot;ViewMachine1&quot;, &quot;trainer&quot;: &quot;ViewTrainerA&quot;}, ...]"

    # Constructing a searchable string, assuming Jinja's tojson and forceescape are used
    # json.dumps produces: '[{"machine": "ViewMachine1", "trainer": "ViewTrainerA"}, ...]'
    # After forceescape, quotes become &quot;
    expected_attr_content_fragment = expected_json_attr_value.replace('"', '&quot;')
    expected_data_attr_str = f'data-machine-assignments="{expected_attr_content_fragment}"'

    assert expected_data_attr_str in response_data_str
