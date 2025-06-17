from unittest.mock import patch
import io

# Helper function to create sample data (can be expanded or moved)
# These are simplified for view tests where we mostly check for presence of data in HTML
def create_sample_view_ppm_entry(SERIAL="PPM_VIEW_S001", status="Upcoming", status_class="warning", **kwargs):
    data = {
        "NO": 1, "EQUIPMENT": "PPM View Device", "MODEL": "PPM-VXYZ", "Name": "PPM Device XYZ View",
        "SERIAL": SERIAL, "MANUFACTURER": "PPM Corp View", "Department": "View Dept",
        "LOG_NO": "VLOG001", "Installation_Date": "01/01/2024", "Warranty_End": "01/01/2026",
        # Eng1-Eng4 removed
        "Status": status, "status_class": status_class,
        "PPM_Q_I": {"engineer": "VQ1 Eng", "quarter_date": "01/04/2024"}, # Added quarter_date
        "PPM_Q_II": {"engineer": "", "quarter_date": "01/07/2024"},
        "PPM_Q_III": {"engineer": "", "quarter_date": "01/10/2024"},
        "PPM_Q_IV": {"engineer": "", "quarter_date": "01/01/2025"},
        "data_type": "ppm", "display_next_maintenance": "N/A (PPM)",
        # Fields for edit form display, derived from PPM_Q_X for convenience in tests
        "Q1_Engineer": "VQ1 Eng", "Q1_Date": "01/04/2024",
        "Q2_Engineer": "", "Q2_Date": "01/07/2024",
        "Q3_Engineer": "", "Q3_Date": "01/10/2024",
        "Q4_Engineer": "", "Q4_Date": "01/01/2025",
    }
    # Allow kwargs to update base data, including nested dicts like PPM_Q_I
    # and ensure Qx_Engineer/Date fields are consistent if PPM_Q_X is updated.
    for key, value in kwargs.items():
        if key in ["PPM_Q_I", "PPM_Q_II", "PPM_Q_III", "PPM_Q_IV"] and isinstance(value, dict):
            data[key].update(value)
            # Update corresponding Qx_Engineer/Date fields if PPM_Q_X is updated by kwargs
            if key == "PPM_Q_I":
                data["Q1_Engineer"] = value.get("engineer", data["Q1_Engineer"])
                data["Q1_Date"] = value.get("quarter_date", data["Q1_Date"])
            elif key == "PPM_Q_II":
                data["Q2_Engineer"] = value.get("engineer", data["Q2_Engineer"])
                data["Q2_Date"] = value.get("quarter_date", data["Q2_Date"])
            elif key == "PPM_Q_III":
                data["Q3_Engineer"] = value.get("engineer", data["Q3_Engineer"])
                data["Q3_Date"] = value.get("quarter_date", data["Q3_Date"])
            elif key == "PPM_Q_IV":
                data["Q4_Engineer"] = value.get("engineer", data["Q4_Engineer"])
                data["Q4_Date"] = value.get("quarter_date", data["Q4_Date"])
        else:
            data[key] = value
    return data

def create_sample_view_ocm_entry(SERIAL="OCM_VIEW_S001", status="Upcoming", status_class="warning", next_maint="01/09/2024", **kwargs):
    data = {
        "NO": 1, "EQUIPMENT": "OCM View Device", "MODEL": "OCM-VABC", "Name": "OCM Device ABC View",
        "SERIAL": SERIAL, "MANUFACTURER": "OCM Corp View", "Department": "View Dept OCM",
        "LOG_NO": "VLOG002", "Installation_Date": "02/01/2024", "Warranty_End": "02/01/2026",
        "Service_Date": "01/03/2024", "Next_Maintenance": next_maint,
        "ENGINEER": "OCM EngX View", "Status": status, "status_class": status_class, # For dashboard/list view
        "PPM": "", "data_type": "ocm", "display_next_maintenance": next_maint
    }
    data.update(kwargs)
    return data

# --- Tests for GET / (Index/Dashboard) ---
def test_index_route_success(client):
    sample_ppm_list = [create_sample_view_ppm_entry("PPMV01")]
    sample_ocm_list = [create_sample_view_ocm_entry("OCMV01")]

    with patch('app.services.data_service.DataService.get_all_entries') as mock_get_all:
        # Configure the mock to return different values based on the call argument
        mock_get_all.side_effect = lambda data_type: sample_ppm_list if data_type == 'ppm' else sample_ocm_list

        response = client.get('/')
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')

        assert "Dashboard" in response_data_str
        assert "PPM View Device" in response_data_str # Check some PPM data
        assert "OCM View Device" in response_data_str # Check some OCM data
        assert "PPMV01" in response_data_str
        assert "OCMV01" in response_data_str
        assert "N/A (PPM)" in response_data_str # display_next_maintenance for PPM
        assert sample_ocm_list[0]["Next_Maintenance"] in response_data_str # display_next_maintenance for OCM

        assert mock_get_all.call_count == 2 # Called for 'ppm' and 'ocm'

def test_index_route_no_data(client):
    with patch('app.services.data_service.DataService.get_all_entries', return_value=[]) as mock_get_all:
        response = client.get('/')
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "No equipment found" in response_data_str or "Total Equipment</h5>\n                    <h2 class=\"card-text\">0</h2>" in response_data_str
        assert mock_get_all.call_count == 2


# --- Tests for GET /equipment/<data_type>/list ---
def test_list_equipment_ppm_success(client):
    sample_ppm_list = [
        create_sample_view_ppm_entry("PPM_L01", Department="DeptX"),
        create_sample_view_ppm_entry("PPM_L02", PPM_Q_I={"engineer": "Eng1Done_PPM_L02", "quarter_date": "10/04/2024"})
    ]
    with patch('app.services.data_service.DataService.get_all_entries', return_value=sample_ppm_list) as mock_get_all:
        response = client.get('/equipment/ppm/list')
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')

        assert "PPM Equipment List" in response_data_str
        assert "PPM_L01" in response_data_str
        assert "PPM_L02" in response_data_str
        assert "DeptX" in response_data_str
        assert "Eng1Done_PPM_L02" in response_data_str # Updated assertion for specific engineer
        assert "VQ1 Eng" in response_data_str # Default Q1 eng for PPM_L01 from helper
        # Check for new PPM specific headers
        assert "<th>Q1 Date</th>" in response_data_str
        assert "<th>Q1 Engineer</th>" in response_data_str
        # Ensure old PPM specific headers are NOT present
        assert "<th>Eng1</th>" not in response_data_str
        assert "<th>Q1 Eng.</th>" not in response_data_str
        # Ensure OCM specific headers are NOT present
        assert "<th>Service Date</th>" not in response_data_str
        mock_get_all.assert_called_once_with('ppm')

def test_list_equipment_ocm_success(client):
    sample_ocm_list = [
        create_sample_view_ocm_entry("OCM_L01", Service_Date="01/07/2024", Next_Maintenance="01/07/2025"),
        create_sample_view_ocm_entry("OCM_L02", ENGINEER="Tech Bob")
    ]
    with patch('app.services.data_service.DataService.get_all_entries', return_value=sample_ocm_list) as mock_get_all:
        response = client.get('/equipment/ocm/list')
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')

        assert "OCM Equipment List" in response_data_str
        assert "OCM_L01" in response_data_str
        assert "OCM_L02" in response_data_str
        assert "01/07/2025" in response_data_str # Next_Maintenance
        assert "Tech Bob" in response_data_str   # Engineer
        # Check for OCM specific headers
        assert "<th>Service Date</th>" in response_data_str
        assert "<th>Next Maintenance</th>" in response_data_str
        # Ensure PPM specific headers are NOT present
        assert "<th>Eng1</th>" not in response_data_str
        mock_get_all.assert_called_once_with('ocm')

def test_list_equipment_no_data(client):
    with patch('app.services.data_service.DataService.get_all_entries', return_value=[]) as mock_get_all:
        response = client.get('/equipment/ppm/list')
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "No PPM equipment found" in response_data_str
        mock_get_all.assert_called_once_with('ppm')

def test_list_equipment_invalid_data_type(client):
    response = client.get('/equipment/xyz/list') # xyz is invalid
    assert response.status_code == 302 # Should redirect
    assert response.location == url_for('views.index', _external=False) # Check Werkzeug docs for _external behavior if needed
    # Check for flashed message (requires session handling, which client does)
    # To check flashed messages, you might need `with client.session_transaction() as sess:` before the request
    # and then check `sess['_flashes']`. Or check if "Invalid equipment type" is in response.data if redirected page shows flashes.
    # For now, just checking redirect is simpler if flash testing is complex here.

from flask import url_for # Import for url_for in redirect check

# --- Tests for Add Equipment Routes (GET and POST) ---

# GET /equipment/ppm/add
def test_add_ppm_equipment_get(client):
    response = client.get('/equipment/ppm/add')
    assert response.status_code == 200
    response_data_str = response.data.decode('utf-8')
    assert "Add PPM Equipment" in response_data_str
    assert "Department" in response_data_str
    assert "Installation_Date" in response_data_str # Optional now
    assert "Eng1" not in response_data_str # Removed
    assert "Q1_Engineer" in response_data_str # New field name

# POST /equipment/ppm/add - Success
def test_add_ppm_equipment_post_success(client):
    form_data = {
        "EQUIPMENT": "New PPM Device", "MODEL": "PPM2K", "SERIAL": "PPM_ADD01",
        "MANUFACTURER": "PPM Makers", "Department": "Main PPM", "LOG_NO": "LOGP01",
        "Installation_Date": "10/10/2023", "Warranty_End": "10/10/2025",
        # Eng1-4 removed
        "Q1_Engineer": "QA Eng", "Q2_Engineer": "QB Eng",
        "Q3_Engineer": "", "Q4_Engineer": "", # Empty engineers should become None
        "Status": "Upcoming", "Name": "" # Optional Name explicitly empty
    }
    # What DataService.add_entry is expected to receive (engineer: None if empty string from form)
    expected_service_payload = {
        "EQUIPMENT": "New PPM Device", "MODEL": "PPM2K", "Name": None,
        "SERIAL": "PPM_ADD01", "MANUFACTURER": "PPM Makers", "Department": "Main PPM",
        "LOG_NO": "LOGP01",
        "Installation_Date": "10/10/2023",
        "Warranty_End": "10/10/2025",
        # Eng1-4 removed
        "Status": "Upcoming", # Or None if empty, then calculated by service
        "PPM_Q_I": {"engineer": "QA Eng"}, "PPM_Q_II": {"engineer": "QB Eng"},
        "PPM_Q_III": {"engineer": None}, "PPM_Q_IV": {"engineer": None}
    }

    with patch('app.services.data_service.DataService.add_entry', return_value=expected_service_payload) as mock_add:
        response = client.post('/equipment/ppm/add', data=form_data, follow_redirects=True)
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "PPM equipment added successfully!" in response_data_str # Flashed message
        assert "PPM Equipment List" in response_data_str # Redirected to list
        mock_add.assert_called_once_with('ppm', expected_service_payload)

# POST /equipment/ppm/add - Validation Error from DataService
def test_add_ppm_equipment_post_validation_error(client):
    form_data = {"EQUIPMENT": "Bad PPM", "SERIAL": "PPM_VALID_ERR"} # Missing many fields
    with patch('app.services.data_service.DataService.add_entry', side_effect=ValueError("Mocked Validation Error from DS")) as mock_add:
        response = client.post('/equipment/ppm/add', data=form_data)
        assert response.status_code == 200 # Re-renders form
        response_data_str = response.data.decode('utf-8')
        assert "Add PPM Equipment" in response_data_str # Still on add page
        assert "Error adding equipment: Mocked Validation Error from DS" in response_data_str # Flashed error
        mock_add.assert_called_once() # Check it was called

# GET /equipment/ocm/add
def test_add_ocm_equipment_get(client):
    response = client.get('/equipment/ocm/add')
    assert response.status_code == 200
    response_data_str = response.data.decode('utf-8')
    assert "Add OCM Equipment" in response_data_str
    assert "Service_Date" in response_data_str
    assert "Next_Maintenance" in response_data_str

# POST /equipment/ocm/add - Success
def test_add_ocm_equipment_post_success(client):
    form_data = {
        "EQUIPMENT": "New OCM Device", "MODEL": "OCM500", "SERIAL": "OCM_ADD01",
        "MANUFACTURER": "OCM Makers", "Department": "Main OCM", "LOG_NO": "LOGO01",
        "Installation_Date": "11/11/2023", "Warranty_End": "11/11/2025",
        "Service_Date": "01/01/2024", "Next_Maintenance": "01/01/2025",
        "ENGINEER": "Tech OCM", "Status": "Upcoming", "PPM": "OptionalLink"
    }
    expected_service_payload = {
        "EQUIPMENT": "New OCM Device", "MODEL": "OCM500", "Name": None,
        "SERIAL": "OCM_ADD01", "MANUFACTURER": "OCM Makers", "Department": "Main OCM",
        "LOG_NO": "LOGO01", "Installation_Date": "11/11/2023", "Warranty_End": "11/11/2025",
        "Service_Date": "01/01/2024", "Next_Maintenance": "01/01/2025",
        "ENGINEER": "Tech OCM", "Status": "Upcoming", "PPM": "OptionalLink"
    }
    with patch('app.services.data_service.DataService.add_entry', return_value=expected_service_payload) as mock_add:
        response = client.post('/equipment/ocm/add', data=form_data, follow_redirects=True)
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "OCM equipment added successfully!" in response_data_str
        assert "OCM Equipment List" in response_data_str
        mock_add.assert_called_once_with('ocm', expected_service_payload)

# POST /equipment/ocm/add - Validation Error
def test_add_ocm_equipment_post_validation_error(client):
    form_data = {"EQUIPMENT": "Bad OCM", "SERIAL": "OCM_VALID_ERR"} # Missing fields
    with patch('app.services.data_service.DataService.add_entry', side_effect=ValueError("OCM Validation Fail")) as mock_add:
        response = client.post('/equipment/ocm/add', data=form_data)
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "Add OCM Equipment" in response_data_str
        assert "Error adding equipment: OCM Validation Fail" in response_data_str
        mock_add.assert_called_once()

# --- Tests for Edit Equipment Routes (GET and POST) ---

# GET /equipment/ppm/edit/<SERIAL>
def test_edit_ppm_equipment_get_exists(client):
    # Helper now includes QX_Date and QX_Engineer directly for template context
    sample_ppm_from_db = create_sample_view_ppm_entry(
        "PPM_EDIT01",
        PPM_Q_I={"engineer": "TestEngQ1", "quarter_date": "05/05/2024"}
    )
    # create_sample_view_ppm_entry will also set sample_ppm_from_db["Q1_Engineer"] and sample_ppm_from_db["Q1_Date"]

    with patch('app.services.data_service.DataService.get_entry', return_value=sample_ppm_from_db) as mock_get:
        response = client.get('/equipment/ppm/edit/PPM_EDIT01')
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "Edit PPM Equipment" in response_data_str
        assert "PPM_EDIT01" in response_data_str # MFG Serial in title/form
        assert 'value="PPM View Device"' in response_data_str # Check equipment name
        assert 'value="TestEngQ1"' in response_data_str # Check Q1_Engineer value in form input
        assert "Q1 Target Date" in response_data_str # Check Q1_Date label
        assert sample_ppm_from_db["Q1_Date"] in response_data_str # Check Q1_Date value displayed
        mock_get.assert_called_once_with('ppm', "PPM_EDIT01")

def test_edit_ppm_equipment_get_not_found(client):
    with patch('app.services.data_service.DataService.get_entry', return_value=None) as mock_get:
        response = client.get('/equipment/ppm/edit/PPM_NO_EXIST', follow_redirects=True)
        assert response.status_code == 200 # Redirects to list
        response_data_str = response.data.decode('utf-8')
        assert "PPM Equipment with serial 'PPM_NO_EXIST' not found." in response_data_str # Flashed message
        assert "PPM Equipment List" in response_data_str
        mock_get.assert_called_once_with('ppm', "PPM_NO_EXIST")

# POST /equipment/ppm/edit/<SERIAL> - Success
def test_edit_ppm_equipment_post_success(client):
    SERIAL = "PPM_EDT_S01"
    # Sample data DataService.get_entry would return (includes calculated dates)
    original_ppm_data_from_db = create_sample_view_ppm_entry(
        SERIAL,
        Name="Original Name",
        PPM_Q_I={"engineer": "OrigQ1Eng", "quarter_date": "10/04/2024"},
        PPM_Q_II={"engineer": "OrigQ2Eng", "quarter_date": "10/07/2024"}
    )

    form_data_update = { # Data from submitted form
        "EQUIPMENT": "Updated PPM Device", "MODEL": "PPM-Pro", "SERIAL": SERIAL,
        "Department": "Pro Dept",
        "Installation_Date": "01/02/2024", # Changed Installation Date
        "Warranty_End": original_ppm_data_from_db["Warranty_End"],
        "MANUFACTURER": original_ppm_data_from_db["MANUFACTURER"],
        "LOG_NO": original_ppm_data_from_db["LOG_NO"], "Name": "", # Name cleared
        # Eng1-4 removed
        "Q1_Engineer": "Q1 Upd", "Q2_Engineer": "Q2 Upd", # Updated engineers
        "Q3_Engineer": "", "Q4_Engineer": "",
        "Status": "" # Let it be recalculated
    }

    # Expected payload to DataService.update_entry
    expected_service_payload = {
        "EQUIPMENT": "Updated PPM Device", "MODEL": "PPM-Pro",
        "Name": None, # Empty string from form becomes None
        "SERIAL": SERIAL,
        "MANUFACTURER": original_ppm_data_from_db["MANUFACTURER"],
        "Department": "Pro Dept", "LOG_NO": original_ppm_data_from_db["LOG_NO"],
        "Installation_Date": "01/02/2024",
        "Warranty_End": original_ppm_data_from_db["Warranty_End"],
        # Eng1-4 removed
        "Status": None, # Will be calculated by service
        "PPM_Q_I": {"engineer": "Q1 Upd"},
        "PPM_Q_II": {"engineer": "Q2 Upd"},
        "PPM_Q_III": {"engineer": None},
        "PPM_Q_IV": {"engineer": None}
    }
    # DataService.update_entry will return the fully updated entry including NO, Status, and calculated quarter_dates
    returned_service_data = expected_service_payload.copy() # Start with what's sent
    # Simulate service adding/modifying these (actual values would depend on mocked date logic in service)
    returned_service_data.update({
        "NO": original_ppm_data_from_db["NO"],
        "Status": "Upcoming",
        "PPM_Q_I": {"engineer": "Q1 Upd", "quarter_date": "01/05/2024"},
        "PPM_Q_II": {"engineer": "Q2 Upd", "quarter_date": "01/08/2024"},
        "PPM_Q_III": {"engineer": None, "quarter_date": "01/11/2024"},
        "PPM_Q_IV": {"engineer": None, "quarter_date": "01/02/2025"}
    })

    with patch('app.services.data_service.DataService.get_entry', return_value=original_ppm_data_from_db), \
         patch('app.services.data_service.DataService.update_entry', return_value=returned_service_data) as mock_update:

        response = client.post(f'/equipment/ppm/edit/{SERIAL}', data=form_data_update, follow_redirects=True)
        assert response.status_code == 200 # After redirect
        assert "PPM equipment updated successfully!" in response_data_str
        assert "PPM Equipment List" in response_data_str
        mock_update.assert_called_once_with('ppm', SERIAL, expected_service_payload)

# POST /equipment/ppm/edit/<SERIAL> - Validation Error
def test_edit_ppm_equipment_post_validation_error(client):
    SERIAL = "PPM_EDT_V_ERR"
    original_ppm_from_db = create_sample_view_ppm_entry(SERIAL) # Helper now sets Qx_Date/Qx_Engineer

    # Simulate form data that would be re-passed to template on error
    form_data_on_error = {
        **original_ppm_from_db, # Base data from DB (including Qx_Date/Engineer for display)
        "Installation_Date": "INVALID DATE", # User's invalid input
        "Q1_Engineer": original_ppm_from_db["PPM_Q_I"]["engineer"], # User's input for engineer fields
        "Q2_Engineer": original_ppm_from_db["PPM_Q_II"]["engineer"],
        "Q3_Engineer": original_ppm_from_db["PPM_Q_III"]["engineer"],
        "Q4_Engineer": original_ppm_from_db["PPM_Q_IV"]["engineer"],
    }
    # Remove Eng1-4 if they are in helper result, though they should be gone by now
    for i in range(1,5): form_data_on_error.pop(f'Eng{i}', None)


    with patch('app.services.data_service.DataService.get_entry', return_value=original_ppm_from_db), \
         patch('app.services.data_service.DataService.update_entry', side_effect=ValueError("PPM Edit Validation Fail")) as mock_update:
        # When POSTing, form data should use QX_Engineer names, not PPM_Q_X_engineer
        response = client.post(f'/equipment/ppm/edit/{SERIAL}', data=form_data_on_error)
        assert response.status_code == 200 # Re-renders form
        response_data_str = response.data.decode('utf-8')
        assert "Edit PPM Equipment" in response_data_str
        assert "Error updating equipment: PPM Edit Validation Fail" in response_data_str
        mock_update.assert_called_once()

# GET /equipment/ocm/edit/<SERIAL>
def test_edit_ocm_equipment_get_exists(client):
    sample_ocm = create_sample_view_ocm_entry("OCM_EDIT01")
    with patch('app.services.data_service.DataService.get_entry', return_value=sample_ocm) as mock_get:
        response = client.get('/equipment/ocm/edit/OCM_EDIT01')
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "Edit OCM Equipment" in response_data_str
        assert "OCM_EDIT01" in response_data_str
        assert 'value="OCM View Device"' in response_data_str
        mock_get.assert_called_once_with('ocm', "OCM_EDIT01")

# POST /equipment/ocm/edit/<SERIAL> - Success
def test_edit_ocm_equipment_post_success(client):
    SERIAL = "OCM_EDT_S01"
    original_ocm_data = create_sample_view_ocm_entry(SERIAL, Next_Maintenance="01/01/2025")

    form_data_update = { # Only fields being changed + SERIAL (readonly)
        "EQUIPMENT": "Updated OCM Device", "MODEL": "OCM-Pro", "SERIAL": SERIAL,
        "Department": original_ocm_data["Department"], "LOG_NO": original_ocm_data["LOG_NO"],
        "Installation_Date": original_ocm_data["Installation_Date"], "Warranty_End": original_ocm_data["Warranty_End"],
        "MANUFACTURER": original_ocm_data["MANUFACTURER"], "ENGINEER": original_ocm_data["ENGINEER"],
        "Service_Date": "15/12/2024", "Next_Maintenance": "15/12/2025", # Updated dates
        "Status": "" # Recalculate
    }
    expected_service_payload = {
        "EQUIPMENT": "Updated OCM Device", "MODEL": "OCM-Pro", "Name": None,
        "SERIAL": SERIAL, "MANUFACTURER": original_ocm_data["MANUFACTURER"],
        "Department": original_ocm_data["Department"], "LOG_NO": original_ocm_data["LOG_NO"],
        "Installation_Date": original_ocm_data["Installation_Date"], "Warranty_End": original_ocm_data["Warranty_End"],
        "Service_Date": "15/12/2024", "Next_Maintenance": "15/12/2025",
        "ENGINEER": original_ocm_data["ENGINEER"], "Status": None, "PPM": ""
    }
    returned_service_data = expected_service_payload.copy()
    returned_service_data["NO"] = 1
    returned_service_data["Status"] = "Upcoming" # Assuming recalculation

    with patch('app.services.data_service.DataService.get_entry', return_value=original_ocm_data), \
         patch('app.services.data_service.DataService.update_entry', return_value=returned_service_data) as mock_update:

        response = client.post(f'/equipment/ocm/edit/{SERIAL}', data=form_data_update, follow_redirects=True)
        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "OCM equipment updated successfully!" in response_data_str
        assert "OCM Equipment List" in response_data_str
        mock_update.assert_called_once_with('ocm', SERIAL, expected_service_payload)


# --- Tests for Delete Equipment Route ---
def test_delete_equipment_ppm_success(client):
    with patch('app.services.data_service.DataService.delete_entry', return_value=True) as mock_delete:
        response = client.post('/equipment/ppm/delete/PPM_DEL_S01', follow_redirects=True)
        assert response.status_code == 200 # Redirects to list
        response_data_str = response.data.decode('utf-8')
        assert "PPM equipment 'PPM_DEL_S01' deleted successfully!" in response_data_str
        assert "PPM Equipment List" in response_data_str
        mock_delete.assert_called_once_with('ppm', 'PPM_DEL_S01')

def test_delete_equipment_ocm_not_found(client):
    with patch('app.services.data_service.DataService.delete_entry', return_value=False) as mock_delete:
        response = client.post('/equipment/ocm/delete/OCM_NODEL_S01', follow_redirects=True)
        assert response.status_code == 200 # Redirects to list
        response_data_str = response.data.decode('utf-8')
        assert "OCM equipment 'OCM_NODEL_S01' not found." in response_data_str
        assert "OCM Equipment List" in response_data_str
        mock_delete.assert_called_once_with('ocm', 'OCM_NODEL_S01')

# --- Tests for Import/Export View Routes ---

# GET /import-export
def test_import_export_page_get(client):
    response = client.get('/import-export')
    assert response.status_code == 200
    response_data_str = response.data.decode('utf-8')
    assert "Import/Export Equipment Data" in response_data_str
    assert "Export All PPM Data" in response_data_str
    assert "Export All OCM Data" in response_data_str

# POST /import
def test_import_equipment_success(client):
    mock_import_results = {"added_count": 5, "updated_count": 2, "skipped_count": 0, "errors": []}
    # Simulate file stream and header reading by DataService
    # The view itself tries to peek at header, then DataService processes the stream.
    # We need to mock DataService.import_data. The header peeking in view is basic.

    # Use new PPM header for inference test, e.g. Q1_Engineer
    csv_content = "EQUIPMENT,MODEL,SERIAL,Q1_Engineer\nDev1,Mod1,SN1,EngA"
    file_stream_bytes = io.BytesIO(csv_content.encode('utf-8'))

    with patch('app.services.data_service.DataService.import_data', return_value=mock_import_results) as mock_ds_import:
        data = {'file': (file_stream_bytes, 'test_import.csv')}
        response = client.post('/import', data=data, content_type='multipart/form-data', follow_redirects=True)

        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "Import successful. 5 new records added. 2 records updated." in response_data_str
        # Assuming redirect to PPM list based on header inference (Q1_Engineer makes it PPM)
        assert "PPM Equipment List" in response_data_str
        mock_ds_import.assert_called_once()
        # We could also assert the type of file_stream passed to mock_ds_import if needed

def test_import_equipment_with_errors_and_skips(client):
    mock_import_results = {
        "added_count": 1, "updated_count": 0, "skipped_count": 2,
        "errors": ["Row 2: Invalid SERIAL", "Row 3: Missing EQUIPMENT"]
    }
    csv_content = "EQUIPMENT,MODEL,SERIAL,Next_Maintenance\nDev1,Mod1,SN1,01/01/2025" # OCM-like header
    file_stream_bytes = io.BytesIO(csv_content.encode('utf-8'))

    with patch('app.services.data_service.DataService.import_data', return_value=mock_import_results) as mock_ds_import:
        data = {'file': (file_stream_bytes, 'test_import_errors.csv')}
        response = client.post('/import', data=data, content_type='multipart/form-data', follow_redirects=True)

        assert response.status_code == 200
        response_data_str = response.data.decode('utf-8')
        assert "Import completed with issues. 1 new records added. 2 records skipped." in response_data_str
        assert "- Row 2: Invalid SERIAL" in response_data_str
        assert "- Row 3: Missing EQUIPMENT" in response_data_str
        assert "OCM Equipment List" in response_data_str # Assuming redirect to OCM list
        mock_ds_import.assert_called_once()

def test_import_equipment_no_file(client):
    response = client.post('/import', content_type='multipart/form-data', data={}, follow_redirects=True)
    assert response.status_code == 200 # Stays on import-export page
    response_data_str = response.data.decode('utf-8')
    assert "No file part selected." in response_data_str
    assert "Import/Export Equipment Data" in response_data_str

def test_import_equipment_wrong_file_type(client):
    data = {'file': (io.BytesIO(b"some text data"), 'test.txt')}
    response = client.post('/import', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    response_data_str = response.data.decode('utf-8')
    assert "Invalid file type. Only CSV files are allowed." in response_data_str
    assert "Import/Export Equipment Data" in response_data_str


# GET /export/ppm and /export/ocm
def test_export_equipment_ppm_success(client):
    sample_csv_data = "NO,EQUIPMENT,MODEL,SERIAL\n1,PPMDev,PModel,PSN001"
    with patch('app.services.data_service.DataService.export_data', return_value=sample_csv_data) as mock_export:
        response = client.get('/export/ppm')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert "attachment; filename=ppm_export.csv" in response.headers['Content-Disposition']
        assert response.data.decode('utf-8') == sample_csv_data
        mock_export.assert_called_once_with(data_type='ppm')

def test_export_equipment_ocm_success(client):
    sample_csv_data = "NO,EQUIPMENT,MODEL,SERIAL\n1,OCMDev,OModel,OSN001"
    with patch('app.services.data_service.DataService.export_data', return_value=sample_csv_data) as mock_export:
        response = client.get('/export/ocm')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert "attachment; filename=ocm_export.csv" in response.headers['Content-Disposition']
        assert response.data.decode('utf-8') == sample_csv_data
        mock_export.assert_called_once_with(data_type='ocm')

def test_export_equipment_service_error(client):
    with patch('app.services.data_service.DataService.export_data', side_effect=Exception("Export Fail")) as mock_export:
        response = client.get('/export/ppm', follow_redirects=True)
        assert response.status_code == 200 # Redirects to import/export page
        response_data_str = response.data.decode('utf-8')
        assert "An error occurred during PPM export: Export Fail" in response_data_str
        assert "Import/Export Equipment Data" in response_data_str
        mock_export.assert_called_once_with(data_type='ppm')
