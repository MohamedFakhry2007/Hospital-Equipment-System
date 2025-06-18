import pytest
from flask import url_for, get_flashed_messages
import json
import os
import shutil

# Attempt to import the Flask app instance
# Common locations are app/__init__.py or app/main.py
try:
    from app import app as flask_app # If app is in app/__init__.py
except ImportError:
    from app.main import app as flask_app # If app is in app.main.py

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
