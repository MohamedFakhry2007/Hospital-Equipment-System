import json
from datetime import datetime, date
from unittest.mock import patch
import io

import pytest
from pydantic import ValidationError

from app.services.data_service import DataService
from app.models.ppm import PPMEntry, QuarterData
from app.models.ocm import OCMEntry
from app.config import Config # To be patched


# Helper functions to create valid data dictionaries
def create_valid_ppm_dict(SERIAL="PPM_SN001", equipment="PPM Device", model="PPM1000", **kwargs):
    base_data = {
        "EQUIPMENT": equipment,
        "MODEL": model,
        "Name": f"{equipment} {model}",
        "SERIAL": SERIAL,
        "MANUFACTURER": "PPM Manufacturer",
        "Department": "PPM Department",
        "LOG_NO": "PPM_LOG001",
        "Installation_Date": "01/01/2023", # Default, can be overridden by kwargs
        "Warranty_End": "01/01/2025",   # Default, can be overridden by kwargs
        # Eng1-Eng4 removed
        "Status": "Upcoming", # Will be recalculated by add/update unless specified
        # PPM_Q_X fields will now also contain quarter_date after service processing
        # For input, they might only have 'engineer'
        "PPM_Q_I": {"engineer": "Q1 Engineer Default"},
        "PPM_Q_II": {"engineer": "Q2 Engineer Default"},
        "PPM_Q_III": {"engineer": ""}, # Default empty engineer
        "PPM_Q_IV": {"engineer": ""},  # Default empty engineer
    }
    # Allow kwargs to override any field, including nested PPM_Q_X fields
    for key, value in kwargs.items():
        if key in ["PPM_Q_I", "PPM_Q_II", "PPM_Q_III", "PPM_Q_IV"] and isinstance(value, dict):
            base_data[key].update(value)
        else:
            base_data[key] = value
    return base_data

def create_valid_ocm_dict(SERIAL="OCM_SN001", equipment="OCM Device", model="OCM1000", **kwargs):
    base_data = {
        "EQUIPMENT": equipment,
        "MODEL": model,
        "Name": f"{equipment} {model}",
        "SERIAL": SERIAL,
        "MANUFACTURER": "OCM Manufacturer",
        "Department": "OCM Department",
        "LOG_NO": "OCM_LOG001",
        "Installation_Date": "01/02/2023",
        "Warranty_End": "01/02/2025",
        "Service_Date": "15/01/2024",
        "Next_Maintenance": "15/01/2025", # Upcoming by default
        "ENGINEER": "OCM Engineer X",
        "Status": "Upcoming", # Will be recalculated by add/update unless specified
        "PPM": "Optional PPM Link", # Optional field
    }
    base_data.update(kwargs)
    return base_data


@pytest.fixture
def mock_data_service(tmp_path, mocker):
    """Fixture for DataService, ensuring data files use tmp_path."""
    ppm_file = tmp_path / "test_ppm.json"
    ocm_file = tmp_path / "test_ocm.json"

    # Patch Config paths
    mocker.patch.object(Config, 'PPM_JSON_PATH', str(ppm_file))
    mocker.patch.object(Config, 'OCM_JSON_PATH', str(ocm_file))

    # Ensure files are created empty for each test
    for f_path in [ppm_file, ocm_file]:
        with open(f_path, 'w') as f:
            json.dump([], f)

    # DataService instance will now use the patched Config paths
    # No need to pass paths to constructor
    service = DataService()
    # Call ensure_data_files_exist to create directory structure if DataService relied on it.
    # DataService.ensure_data_files_exist() # This is called internally by load/save

    return service


def test_add_ppm_entry(mock_data_service):
    """Test adding a new PPM entry."""
    data = create_valid_ppm_dict(SERIAL="PPM_S001")
    added_entry = mock_data_service.add_entry("ppm", data)

    assert added_entry["SERIAL"] == "PPM_S001"
    assert added_entry["NO"] == 1
    # Status calculation will now depend on quarter_dates and engineers.
    # _calculate_ppm_quarter_dates will run, using today if Installation_Date is problematic.
    # Let's assume default "Upcoming" or test more specifically later.
    # For now, we'll focus on the structure.
    assert "PPM_Q_I" in added_entry
    assert "quarter_date" in added_entry["PPM_Q_I"] # Service should have added this

    all_entries = mock_data_service.get_all_entries("ppm")
    assert len(all_entries) == 1
    # Compare relevant fields, NO and Status are auto-set
    retrieved_entry = mock_data_service.get_entry("ppm", "PPM_S001")
    assert retrieved_entry["MODEL"] == data["MODEL"]


def test_add_ocm_entry(mock_data_service):
    """Test adding a new OCM entry."""
    data = create_valid_ocm_dict(SERIAL="OCM_S001", Next_Maintenance="01/01/2025") # Future date
    added_entry = mock_data_service.add_entry("ocm", data)
    assert added_entry["SERIAL"] == "OCM_S001"
    assert added_entry["NO"] == 1
    assert added_entry["Status"] == "Upcoming" # Based on Next_Maintenance being in future
    all_entries = mock_data_service.get_all_entries("ocm")
    assert len(all_entries) == 1


def test_add_duplicate_SERIAL(mock_data_service):
    """Test adding an entry with a duplicate SERIAL."""
    data1 = create_valid_ppm_dict(SERIAL="DUP001")
    mock_data_service.add_entry("ppm", data1)

    data2 = create_valid_ppm_dict(SERIAL="DUP001", EQUIPMENT="Another Device")
    with pytest.raises(ValueError, match="Duplicate SERIAL detected: DUP001"):
        mock_data_service.add_entry("ppm", data2)


def test_update_ppm_entry(mock_data_service, mocker):
    """Test updating an existing PPM entry."""
    # Mock today for consistent quarter date calculation by the service
    fixed_today = date(2023, 1, 10) # Example: Jan 10, 2023
    # Mock datetime.date.today() within the service's scope for _calculate_ppm_quarter_dates
    mocker.patch('app.services.data_service.datetime').today.return_value = fixed_today

    original_data_input = create_valid_ppm_dict(
        SERIAL="PPM_U001",
        Installation_Date="01/01/2023", # Q1 will be 01/04/2023
        PPM_Q_I={"engineer": "Eng Q1 Orig"}
    )
    # DataService.add_entry will calculate initial quarter_dates and status
    initial_added_entry = mock_data_service.add_entry("ppm", original_data_input)
    assert initial_added_entry["PPM_Q_I"]["engineer"] == "Eng Q1 Orig"
    assert initial_added_entry["PPM_Q_I"]["quarter_date"] == "01/04/2023"

    update_payload_form_input = { # Mimics form input, only engineer might be provided for quarters
        "MODEL": "PPM1000-rev2",
        "PPM_Q_I": {"engineer": "Eng Q1 Updated"},
        "PPM_Q_II": {"engineer": "Eng Q2 New"},
        "Installation_Date": "01/02/2023" # Change installation date, should trigger new quarter_dates
    }

    # DataService.update_entry expects a full model-like dict, but it will re-calculate quarter_dates
    # and status. So, we base the full update dict on the original structure but apply changes.
    # The service will handle filling in missing quarter_dates in the update_payload.

    # Construct the full data for update_entry based on what would be submitted (merged by view)
    # The view would typically pass the full existing entry merged with form changes.
    # Here, we simulate that `update_entry` receives the necessary fields for validation,
    # and it will recalculate quarter_dates based on the new Installation_Date.

    # Simulate a full payload as if prepared by views.py from form + existing data
    # For update_entry, it's important that all required model fields are present.
    # The service then recalculates quarter_dates and status.
    data_for_update_service = initial_added_entry.copy() # Start with the full current state
    data_for_update_service["MODEL"] = update_payload_form_input["MODEL"]
    data_for_update_service["Installation_Date"] = update_payload_form_input["Installation_Date"]
    # Update engineer info for quarters based on "form input"
    data_for_update_service["PPM_Q_I"]["engineer"] = update_payload_form_input["PPM_Q_I"]["engineer"]
    # If Q_II was empty before, and now gets an engineer
    data_for_update_service["PPM_Q_II"] = update_payload_form_input["PPM_Q_II"]


    returned_updated_entry = mock_data_service.update_entry("ppm", "PPM_U001", data_for_update_service)

    assert returned_updated_entry["MODEL"] == "PPM1000-rev2"
    assert returned_updated_entry["PPM_Q_I"]["engineer"] == "Eng Q1 Updated"
    assert returned_updated_entry["PPM_Q_II"]["engineer"] == "Eng Q2 New"

    # Check if quarter dates were recalculated based on new Installation_Date "01/02/2023"
    # Q1 should be 01/05/2023, Q2 01/08/2023 etc.
    assert returned_updated_entry["PPM_Q_I"]["quarter_date"] == "01/05/2023"
    assert returned_updated_entry["PPM_Q_II"]["quarter_date"] == "01/08/2023"
    assert returned_updated_entry["NO"] == 1 # NO should be preserved
    # Status would also be recalculated, test separately or verify if logic is simple enough.


def test_update_ocm_next_maintenance_to_overdue(mock_data_service, mocker):
    """Test OCM entry status changes to Overdue when Next_Maintenance is updated to past."""
    # Mock current date to be fixed
    fixed_now = datetime(2024, 3, 15) # March 15, 2024
    mocker.patch('app.services.data_service.datetime', now=lambda: fixed_now)

    original_data = create_valid_ocm_dict(SERIAL="OCM_U002", Next_Maintenance="01/04/2024") # Upcoming
    mock_data_service.add_entry("ocm", original_data)
    assert mock_data_service.get_entry("ocm", "OCM_U002")["Status"] == "Upcoming"

    update_payload = {"Next_Maintenance": "01/03/2024"} # Now in the past relative to fixed_now
    updated_data_full = original_data.copy()
    updated_data_full.update(update_payload)

    returned_updated_entry = mock_data_service.update_entry("ocm", "OCM_U002", updated_data_full)
    assert returned_updated_entry["Next_Maintenance"] == "01/03/2024"
    assert returned_updated_entry["Status"] == "Overdue"


def test_update_nonexistent_entry(mock_data_service):
    """Test updating a non-existent entry."""
    update_data = create_valid_ppm_dict(SERIAL="NONEXISTENT")
    with pytest.raises(KeyError, match="Entry with SERIAL 'NONEXISTENT' not found for update."):
        mock_data_service.update_entry("ppm", "NONEXISTENT", update_data)


def test_update_SERIAL_not_allowed(mock_data_service):
    """Test attempting to update SERIAL."""
    original_data = create_valid_ppm_dict(SERIAL="SERIAL_ORIG")
    mock_data_service.add_entry("ppm", original_data)

    update_data = original_data.copy()
    update_data["SERIAL"] = "SERIAL_NEW" # Attempting to change SERIAL

    with pytest.raises(ValueError, match="Cannot change SERIAL"):
        mock_data_service.update_entry("ppm", "SERIAL_ORIG", update_data)


def test_delete_entry(mock_data_service):
    """Test deleting an existing entry and reindexing."""
    data1 = create_valid_ppm_dict(SERIAL="DEL_S001")
    data2 = create_valid_ppm_dict(SERIAL="DEL_S002")
    mock_data_service.add_entry("ppm", data1) # NO=1
    mock_data_service.add_entry("ppm", data2) # NO=2

    assert mock_data_service.delete_entry("ppm", "DEL_S001") is True
    all_entries = mock_data_service.get_all_entries("ppm")
    assert len(all_entries) == 1
    assert mock_data_service.get_entry("ppm", "DEL_S001") is None
    # Check if reindexing worked
    remaining_entry = mock_data_service.get_entry("ppm", "DEL_S002")
    assert remaining_entry is not None
    assert remaining_entry["NO"] == 1 # Should be reindexed to 1


def test_delete_nonexistent_entry(mock_data_service):
    """Test deleting a non-existent entry."""
    assert mock_data_service.delete_entry("ppm", "NONEXISTENT_DEL") is False


def test_get_all_entries(mock_data_service):
    """Test getting all entries."""
    data1 = create_valid_ppm_dict(SERIAL="GETALL_S001")
    data2 = create_valid_ppm_dict(SERIAL="GETALL_S002")
    mock_data_service.add_entry("ppm", data1)
    mock_data_service.add_entry("ppm", data2)

    all_entries = mock_data_service.get_all_entries("ppm")
    assert len(all_entries) == 2
    # Entries in all_entries will have 'NO' and calculated 'Status'
    # We need to compare based on a common key like SERIAL
    SERIALs_retrieved = {e["SERIAL"] for e in all_entries}
    assert "GETALL_S001" in SERIALs_retrieved
    assert "GETALL_S002" in SERIALs_retrieved


def test_get_entry(mock_data_service):
    """Test getting a specific entry by SERIAL."""
    data = create_valid_ocm_dict(SERIAL="GET_S001")
    mock_data_service.add_entry("ocm", data)

    retrieved_entry = mock_data_service.get_entry("ocm", "GET_S001")
    assert retrieved_entry is not None
    assert retrieved_entry["MODEL"] == data["MODEL"]
    assert retrieved_entry["NO"] == 1


def test_get_nonexistent_entry(mock_data_service):
    """Test getting a non-existent entry."""
    assert mock_data_service.get_entry("ppm", "NONEXISTENT_GET") is None


# Tests for ensure_unique_SERIAL and reindex are implicitly covered by add/delete tests.

# --- New tests for load_data ---
def test_load_data_valid_ppm(mock_data_service, tmp_path):
    ppm_file = tmp_path / "test_ppm.json"
    valid_entry_dict = create_valid_ppm_dict(SERIAL="LD_PPM01")
    # Manually save data to simulate existing file
    with open(ppm_file, 'w') as f:
        json.dump([valid_entry_dict], f)

    loaded_data = mock_data_service.load_data("ppm")
    assert len(loaded_data) == 1
    assert loaded_data[0]["SERIAL"] == "LD_PPM01"

def test_load_data_valid_ocm(mock_data_service, tmp_path):
    ocm_file = tmp_path / "test_ocm.json"
    valid_entry_dict = create_valid_ocm_dict(SERIAL="LD_OCM01")
    with open(ocm_file, 'w') as f:
        json.dump([valid_entry_dict], f)

    loaded_data = mock_data_service.load_data("ocm")
    assert len(loaded_data) == 1
    assert loaded_data[0]["SERIAL"] == "LD_OCM01"

def test_load_data_skips_invalid_entries(mock_data_service, tmp_path, caplog):
    ppm_file = tmp_path / "test_ppm.json"
    valid_entry = create_valid_ppm_dict(SERIAL="VALID01")
    invalid_entry_dict = create_valid_ppm_dict(SERIAL="INVALID01")
    invalid_entry_dict["Installation_Date"] = "invalid-date-format" # Invalid data

    with open(ppm_file, 'w') as f:
        json.dump([valid_entry, invalid_entry_dict], f)

    loaded_data = mock_data_service.load_data("ppm")
    assert len(loaded_data) == 1 # Should skip the invalid one
    assert loaded_data[0]["SERIAL"] == "VALID01"
    assert "Data validation error loading ppm entry INVALID01" in caplog.text
    assert "Skipping this entry." in caplog.text


def test_load_data_empty_json_file(mock_data_service, tmp_path):
    ppm_file = tmp_path / "test_ppm.json"
    with open(ppm_file, 'w') as f:
        json.dump([], f)
    loaded_data = mock_data_service.load_data("ppm")
    assert len(loaded_data) == 0

def test_load_data_malformed_json_file(mock_data_service, tmp_path, caplog):
    ppm_file = tmp_path / "test_ppm.json"
    with open(ppm_file, 'w') as f:
        f.write("[{'SERIAL': 'MALFORMED'}]") # Malformed JSON (single quotes)

    loaded_data = mock_data_service.load_data("ppm")
    assert len(loaded_data) == 0
    assert f"Error decoding JSON from {ppm_file}" in caplog.text

def test_load_data_file_not_found(mock_data_service, tmp_path, mocker, caplog):
    # Ensure the file does not exist by pointing to a new non-existent file
    non_existent_ppm_file = tmp_path / "non_existent_ppm.json"
    mocker.patch.object(Config, 'PPM_JSON_PATH', str(non_existent_ppm_file))

    # DataService.ensure_data_files_exist() inside load_data will try to create it.
    # To test FileNotFoundError for reading, we'd need to make ensure_data_files_exist fail or make file unreadable.
    # The current load_data creates it if not found, then tries to read. If it's empty, it's fine.
    # If ensure_data_files_exist was not there, then FileNotFoundError would be more direct.
    # Let's test the "empty list if file not found then created empty" scenario.
    loaded_data = DataService.load_data("ppm") # Use class method directly to bypass fixture's own file creation
    assert loaded_data == []
    # If ensure_data_files_exist is robust, it might not log "file not found" but create it.
    # The current implementation of load_data has ensure_data_files_exist()
    # then tries to open. If ensure_data_files_exist() works, open won't cause FileNotFoundError.
    # Instead, it will be an empty file, and json.loads("") will fail or return [].
    # The code returns [] if content is empty string.
    # If the file truly cannot be created or accessed, an IOError or similar might occur.
    # The current `load_data` catches generic Exception.
    # Let's simulate a read error post-ensure_data_files_exist for more specific test
    mocker.patch('builtins.open', mocker.mock_open(read_data="invalid json content"))
    mocker.patch('json.loads', side_effect=json.JSONDecodeError("Simulated error", "doc", 0))
    loaded_data = DataService.load_data("ppm")
    assert loaded_data == []
    assert "Error decoding JSON" in caplog.text


# --- New tests for save_data ---
def test_save_data_ppm(mock_data_service, tmp_path):
    ppm_file = tmp_path / "test_ppm.json"
    entry1 = create_valid_ppm_dict(SERIAL="SAVE_PPM01")
    entry2 = create_valid_ppm_dict(SERIAL="SAVE_PPM02")
    data_to_save = [entry1, entry2]

    mock_data_service.save_data(data_to_save, "ppm")

    with open(ppm_file, 'r') as f:
        saved_data_on_disk = json.load(f)

    assert len(saved_data_on_disk) == 2
    assert saved_data_on_disk[0]["SERIAL"] == "SAVE_PPM01"
    assert saved_data_on_disk[1]["SERIAL"] == "SAVE_PPM02"

def test_save_data_ocm(mock_data_service, tmp_path):
    ocm_file = tmp_path / "test_ocm.json"
    entry1 = create_valid_ocm_dict(SERIAL="SAVE_OCM01")
    data_to_save = [entry1]

    mock_data_service.save_data(data_to_save, "ocm")

    with open(ocm_file, 'r') as f:
        saved_data_on_disk = json.load(f)
    assert len(saved_data_on_disk) == 1
    assert saved_data_on_disk[0]["SERIAL"] == "SAVE_OCM01"


# --- New tests for calculate_status ---
@pytest.mark.parametrize("service_date_str, next_maintenance_str, expected_status", [
    ("01/01/2024", "01/06/2024", "Upcoming"), # Next maint in future
    (None, "01/06/2024", "Upcoming"),          # Next maint in future, no service date
    ("01/01/2024", "01/02/2024", "Overdue"),   # Next maint in past
    (None, "01/02/2024", "Overdue"),           # Next maint in past, no service date
    # Maintained: Service date is >= next maintenance date (this rule might need refinement)
    # Or, more practically, service date is recent and next maintenance is well in future.
    # The current logic is: if service_date >= next_maintenance_date -> Maintained
    # This means if you serviced it ON the day it was next due, it's maintained.
    # ("01/06/2024", "01/06/2024", "Maintained"), # Serviced on due date
    # ("15/06/2024", "01/06/2024", "Maintained"), # Serviced after due date (catches up)
    # Let's assume 'Maintained' means the *last* service was done appropriately
    # and the *next* is not yet due.
    # If Next_Maintenance = 01/06/2024, Service_Date = 01/05/2024 -> Upcoming (last service done, next one pending)
    ("01/05/2024", "01/06/2024", "Upcoming"),
    # If Next_Maintenance = 01/02/2024 (past), Service_Date = 01/01/2024 (older) -> Overdue
    ("01/01/2024", "01/02/2024", "Overdue"),
    # If Next_Maintenance = 01/06/2024, Service_Date = 01/06/2024 (serviced today for today) -> Maintained
    # This case is tricky. calculate_status might consider this "Maintained" if service_date >= next_maintenance_date
    # Let's test the actual behavior of the implemented logic.
    # Current: if service_date >= next_maintenance_date -> Maintained.
    #          else if next_maintenance_date < today -> Overdue. else Upcoming.
])
def test_calculate_status_ocm(mock_data_service, mocker, service_date_str, next_maintenance_str, expected_status):
    # Mock current date for consistent testing
    # Let's say today is March 15, 2024
    fixed_today = date(2024, 3, 15)
    mocker.patch('app.services.data_service.datetime', now=lambda: datetime(fixed_today.year, fixed_today.month, fixed_today.day))

    ocm_entry_data = {
        "Service_Date": service_date_str,
        "Next_Maintenance": next_maintenance_str,
        # Other fields are not strictly needed for this status calculation
        "SERIAL": "TestOCMStatus"
    }
    status = mock_data_service.calculate_status(ocm_entry_data, "ocm")
    assert status == expected_status

# Test specific OCM Maintained cases based on current logic
def test_calculate_status_ocm_maintained_cases(mock_data_service, mocker):
    fixed_today = date(2024, 3, 15)
    mocker.patch('app.services.data_service.datetime', now=lambda: datetime(fixed_today.year, fixed_today.month, fixed_today.day))

    # Case 1: Serviced on the day it was due (for a future due date relative to today)
    # If Next_Maintenance was 01/03/2024 and Service_Date is 01/03/2024, and today is 15/03/2024
    # This means the maintenance that was due on 01/03/2024 was done.
    # The *next* Next_Maintenance should be in the future.
    # The current calculate_status is simpler: if service_date >= next_maintenance_date -> Maintained
    # This interpretation is tricky. Let's test what it does.
    # If Next_Maintenance is 01/03/2024 (past due) and Service_Date is 01/03/2024, it's Maintained.
    entry1 = {"Service_Date": "01/03/2024", "Next_Maintenance": "01/03/2024"}
    assert mock_data_service.calculate_status(entry1, "ocm") == "Maintained"

    # Case 2: Serviced after it was due (for a past due date)
    entry2 = {"Service_Date": "10/03/2024", "Next_Maintenance": "01/03/2024"}
    assert mock_data_service.calculate_status(entry2, "ocm") == "Maintained"

    # Case 3: Next maintenance is in future, service date is also in future but before next_maint (invalid scenario but test)
    # This should be Upcoming, as the service hasn't happened.
    entry3 = {"Service_Date": "01/04/2024", "Next_Maintenance": "01/05/2024"} # Both future
    assert mock_data_service.calculate_status(entry3, "ocm") == "Upcoming"


from dateutil.relativedelta import relativedelta

# Test for _calculate_ppm_quarter_dates
def test_calculate_ppm_quarter_dates(mock_data_service, mocker):
    # Mock datetime.today() for predictable results when no installation_date is given
    fixed_today = date(2023, 1, 15) # January 15, 2023
    mocker.patch('app.services.data_service.datetime').today.return_value = fixed_today

    # Scenario 1: Valid installation_date_str
    install_date_str = "01/10/2022" # Oct 1, 2022
    q_dates = DataService._calculate_ppm_quarter_dates(install_date_str)
    expected_q1 = (datetime.strptime(install_date_str, "%d/%m/%Y") + relativedelta(months=3)).strftime("%d/%m/%Y")
    expected_q2 = (datetime.strptime(expected_q1, "%d/%m/%Y") + relativedelta(months=3)).strftime("%d/%m/%Y")
    expected_q3 = (datetime.strptime(expected_q2, "%d/%m/%Y") + relativedelta(months=3)).strftime("%d/%m/%Y")
    expected_q4 = (datetime.strptime(expected_q3, "%d/%m/%Y") + relativedelta(months=3)).strftime("%d/%m/%Y")
    assert q_dates == [expected_q1, expected_q2, expected_q3, expected_q4]
    assert q_dates[0] == "01/01/2023"
    assert q_dates[3] == "01/10/2023" # Check year change

    # Scenario 2: installation_date_str is None
    q_dates_none = DataService._calculate_ppm_quarter_dates(None)
    expected_q1_from_today = (fixed_today + relativedelta(months=3)).strftime("%d/%m/%Y")
    assert q_dates_none[0] == expected_q1_from_today
    assert q_dates_none[0] == "15/04/2023"

    # Scenario 3: installation_date_str is empty
    q_dates_empty = DataService._calculate_ppm_quarter_dates("")
    assert q_dates_empty[0] == expected_q1_from_today # Should also use today

    # Scenario 4: Invalid installation_date_str format
    q_dates_invalid = DataService._calculate_ppm_quarter_dates("invalid-date")
    assert q_dates_invalid[0] == expected_q1_from_today # Should use today


# Updated tests for PPM status calculation
@pytest.mark.parametrize("ppm_quarters_data, expected_status, today_str", [
    # Scenario: Overdue (past date, no engineer)
    ({"PPM_Q_I": {"quarter_date": "01/01/2024", "engineer": None}}, "Overdue", "15/03/2024"),
    ({"PPM_Q_I": {"quarter_date": "01/01/2024", "engineer": ""}}, "Overdue", "15/03/2024"),
    # Scenario: Overdue (multiple past, one missing engineer)
    ({
        "PPM_Q_I": {"quarter_date": "01/10/2023", "engineer": "EngA"},
        "PPM_Q_II": {"quarter_date": "01/01/2024", "engineer": None}
    }, "Overdue", "15/03/2024"),
    # Scenario: Maintained (all past quarters have engineers)
    ({
        "PPM_Q_I": {"quarter_date": "01/10/2023", "engineer": "EngA"},
        "PPM_Q_II": {"quarter_date": "01/01/2024", "engineer": "EngB"}
    }, "Maintained", "15/03/2024"),
    # Scenario: Upcoming (all future dates, no engineers)
    ({
        "PPM_Q_I": {"quarter_date": "01/04/2024", "engineer": None},
        "PPM_Q_II": {"quarter_date": "01/07/2024", "engineer": None}
    }, "Upcoming", "15/03/2024"),
    # Scenario: Upcoming (all future dates, some engineers)
    ({
        "PPM_Q_I": {"quarter_date": "01/04/2024", "engineer": "EngA"},
        "PPM_Q_II": {"quarter_date": "01/07/2024", "engineer": None}
    }, "Upcoming", "15/03/2024"), # Still upcoming as no past due items.
    # Scenario: Mixed - past maintained, future upcoming
    ({
        "PPM_Q_I": {"quarter_date": "01/01/2024", "engineer": "EngA"}, # Past, maintained
        "PPM_Q_II": {"quarter_date": "01/04/2024", "engineer": None}  # Future, no eng
    }, "Maintained", "15/03/2024"), # Considered Maintained because past work is done.
    # Scenario: Upcoming (no past due quarters, but no engineers assigned yet for future)
    ({ "PPM_Q_I": {"quarter_date": "01/06/2024", "engineer": None} }, "Upcoming", "15/03/2024"),
    # Scenario: Upcoming (one quarter with no date info - should not make it overdue)
    ({ "PPM_Q_I": {"engineer": "EngA"} }, "Upcoming", "15/03/2024"),
    # Scenario: Maintained (only one past quarter, and it's maintained)
    ({ "PPM_Q_I": {"quarter_date": "01/01/2024", "engineer": "EngA"} }, "Maintained", "15/03/2024"),
])
def test_calculate_status_ppm_new_logic(mock_data_service, mocker, ppm_quarters_data, expected_status, today_str):
    fixed_today = datetime.strptime(today_str, "%d/%m/%Y").date()
    mocker.patch('app.services.data_service.datetime', now=lambda: datetime(fixed_today.year, fixed_today.month, fixed_today.day))

    ppm_entry_data = {"SERIAL": "TestPPMStatus"}
    ppm_entry_data.update(ppm_quarters_data) # Add PPM_Q_X data

    status = mock_data_service.calculate_status(ppm_entry_data, "ppm")
    assert status == expected_status


# --- Tests for add_entry with status ---
def test_add_ppm_entry_calculates_status_new(mock_data_service, mocker):
    # Mock today for consistent quarter date calculation by the service
    fixed_today = date(2023, 1, 10)
    mocker.patch('app.services.data_service.datetime').today.return_value = fixed_today

    # This data will have quarter_dates calculated from fixed_today + 3,6,9,12 months, all future
    # Example: Q1_date = 10/04/2023, Q2_date = 10/07/2023 etc.
    # Since all dates are future, status should be Upcoming.
    data_no_status = create_valid_ppm_dict(
        SERIAL="PPM_ADD_S001",
        Installation_Date=None, # Will use fixed_today for quarter calculation base
        PPM_Q_I={"engineer": "EngTest"} # Only engineer provided
    )
    if "Status" in data_no_status: del data_no_status["Status"]

    added_entry = mock_data_service.add_entry("ppm", data_no_status)
    assert added_entry["Status"] == "Upcoming" # All calculated quarter dates will be future
    assert "quarter_date" in added_entry["PPM_Q_I"]
    assert added_entry["PPM_Q_I"]["quarter_date"] == "10/04/2023"


def test_add_ocm_entry_calculates_status(mock_data_service, mocker):
    fixed_today = date(2024, 3, 15)
    mocker.patch('app.services.data_service.datetime', now=lambda: datetime(fixed_today.year, fixed_today.month, fixed_today.day))

    data_overdue = create_valid_ocm_dict(SERIAL="OCM_ADD_S001", Next_Maintenance="01/01/2024", Service_Date=None)
    if "Status" in data_overdue: del data_overdue["Status"]
    added_entry = mock_data_service.add_entry("ocm", data_overdue)
    assert added_entry["Status"] == "Overdue"

    data_upcoming = create_valid_ocm_dict(SERIAL="OCM_ADD_S002", Next_Maintenance="01/06/2024", Service_Date=None)
    if "Status" in data_upcoming: del data_upcoming["Status"]
    added_entry_2 = mock_data_service.add_entry("ocm", data_upcoming)
    assert added_entry_2["Status"] == "Upcoming"

# --- Tests for update_entry with status ---
def test_update_ppm_entry_recalculates_status_new(mock_data_service, mocker):
    fixed_today = date(2024, 3, 15)
    mocker.patch('app.services.data_service.datetime', now=lambda: datetime(fixed_today.year, fixed_today.month, fixed_today.day))
    mocker.patch('app.services.data_service.datetime').today.return_value = fixed_today # For _calculate_ppm_quarter_dates

    # Initial entry: Q1 is past & no engineer -> Overdue
    ppm_data_initial = create_valid_ppm_dict(
        SERIAL="PPM_UPD_S001",
        Installation_Date="01/09/2023", # Q1=01/12/2023 (past), Q2=01/03/2024 (past)
        PPM_Q_I={"engineer": None},
        PPM_Q_II={"engineer": "EngB"}
    )
    if "Status" in ppm_data_initial: del ppm_data_initial["Status"]
    added_initial_entry = mock_data_service.add_entry("ppm", ppm_data_initial)
    assert added_initial_entry["Status"] == "Overdue" # Q1 was past and no engineer

    # Update: Provide engineer for Q1
    # The service's update_entry will re-calculate quarter dates based on Installation_Date
    # and then re-calculate status.
    update_payload_form_input = {"PPM_Q_I": {"engineer": "EngA_Now"}}

    # Construct full data for service update
    data_for_update_service = added_initial_entry.copy()
    data_for_update_service["PPM_Q_I"]["engineer"] = update_payload_form_input["PPM_Q_I"]["engineer"]
    if "Status" in data_for_update_service: del data_for_update_service["Status"] # Ensure status is recalculated

    updated_entry = mock_data_service.update_entry("ppm", "PPM_UPD_S001", data_for_update_service)
    # Now Q1 (01/12/2023) has EngA_Now, Q2 (01/03/2024) has EngB. Both past.
    # All past quarters are maintained.
    assert updated_entry["Status"] == "Maintained"

# --- Tests for import_data ---

def create_csv_string(headers, data_rows):
    """Helper to create a CSV string."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for row in data_rows:
        writer.writerow(row)
    return output.getvalue()

# Dynamically get headers from Pydantic models for testing import/export
PPM_MODEL_FIELDS = list(PPMEntry.model_fields.keys())
OCM_MODEL_FIELDS = list(OCMEntry.model_fields.keys())

# Remove 'NO' as it's not expected in import CSV file, but present in model for export
PPM_CSV_IMPORT_HEADERS = [h for h in PPM_MODEL_FIELDS if h != 'NO']
OCM_CSV_IMPORT_HEADERS = [h for h in OCM_MODEL_FIELDS if h != 'NO']


def test_import_data_new_ppm_entries(mock_data_service):
# Define new PPM CSV headers for import tests
PPM_CSV_IMPORT_HEADERS_NEW = [
    'EQUIPMENT', 'MODEL', 'Name', 'SERIAL', 'MANUFACTURER', 'Department',
    'LOG_NO', 'Installation_Date', 'Warranty_End', 'Status', 'OCM',
    'Q1_Engineer', 'Q2_Engineer', 'Q3_Engineer', 'Q4_Engineer'
]

def test_import_data_new_ppm_entries_updated_format(mock_data_service, mocker):
    fixed_today = date(2023, 1, 10)
    mocker.patch('app.services.data_service.datetime').today.return_value = fixed_today

    csv_rows = [
        { # Entry 1: All info, explicit status
            "EQUIPMENT": "PPM Device 1", "MODEL": "P1000", "Name": "PPM Alpha", "SERIAL": "IMP_PPM01_NEW",
            "MANUFACTURER": "Manuf", "Department": "DeptX", "LOG_NO": "L001",
            "Installation_Date": "01/10/2022", "Warranty_End": "01/10/2024",
            "Status": "Upcoming", "OCM": "",
            "Q1_Engineer": "EngA", "Q2_Engineer": "EngB", "Q3_Engineer": "", "Q4_Engineer": ""
        },
        { # Entry 2: Minimal info, let status and quarter dates be calculated
            "EQUIPMENT": "PPM Device 2", "MODEL": "P2000", "Name": "", "SERIAL": "IMP_PPM02_NEW",
            "MANUFACTURER": "Manuf", "Department": "DeptY", "LOG_NO": "L002",
            "Installation_Date": "", "Warranty_End": "", # Optional dates empty
            "Status": "", "OCM": "",
            "Q1_Engineer": "EngC", "Q2_Engineer": "", "Q3_Engineer": "", "Q4_Engineer": ""
        }
    ]
    csv_content = create_csv_string(PPM_CSV_IMPORT_HEADERS_NEW, csv_rows)
    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))

    assert result["added_count"] == 2, f"Errors: {result['errors']}"
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 0
    assert not result["errors"]

    entry1_db = mock_data_service.get_entry("ppm", "IMP_PPM01_NEW")
    assert entry1_db is not None
    assert entry1_db["Status"] == "Upcoming" # Used provided
    assert entry1_db["PPM_Q_I"]["engineer"] == "EngA"
    assert entry1_db["PPM_Q_I"]["quarter_date"] == "01/01/2023" # Calculated from 01/10/2022
    assert entry1_db["Installation_Date"] == "01/10/2022"

    entry2_db = mock_data_service.get_entry("ppm", "IMP_PPM02_NEW")
    assert entry2_db is not None
    # Status for entry2: Install date empty, so quarter_dates from fixed_today (all future).
    # Q1_Engineer is EngC. All future dates, one engineer -> Upcoming.
    assert entry2_db["Status"] == "Upcoming"
    assert entry2_db["PPM_Q_I"]["engineer"] == "EngC"
    assert entry2_db["PPM_Q_I"]["quarter_date"] == "10/04/2023" # Calculated from fixed_today
    assert entry2_db["Installation_Date"] is None # Was empty in CSV


def test_import_data_new_ocm_entries(mock_data_service, mocker): # Keep OCM tests as they are good
    fixed_today = date(2024, 3, 15)
    mocker.patch('app.services.data_service.datetime', now=lambda: datetime(fixed_today.year, fixed_today.month, fixed_today.day))

    ocm_entry_1 = create_valid_ocm_dict(SERIAL="IMP_OCM01", Next_Maintenance="01/01/2024") # Overdue
    ocm_entry_2 = create_valid_ocm_dict(SERIAL="IMP_OCM02", Next_Maintenance="01/06/2024") # Upcoming
    # Remove status so it's calculated by import_data
    del ocm_entry_1["Status"]
    del ocm_entry_2["Status"]

    csv_rows = [
        {k: v for k, v in ocm_entry_1.items() if k != 'NO'},
        {k: v for k, v in ocm_entry_2.items() if k != 'NO'}
    ]
    csv_content = create_csv_string(OCM_CSV_IMPORT_HEADERS, csv_rows)

    result = mock_data_service.import_data("ocm", io.StringIO(csv_content))

    assert result["added_count"] == 2
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 0
    assert not result["errors"]

    entry1_db = mock_data_service.get_entry("ocm", "IMP_OCM01")
    assert entry1_db["Status"] == "Overdue"
    entry2_db = mock_data_service.get_entry("ocm", "IMP_OCM02")
    assert entry2_db["Status"] == "Upcoming"


def test_import_data_updates_existing_entries(mock_data_service):
    # Pre-populate data
    existing_ppm_data = create_valid_ppm_dict(
        SERIAL="EXIST_PPM01_NEW",
        MODEL="OldModel",
        Installation_Date="01/01/2023", # Q1=01/04/2023
        PPM_Q_I={"engineer": "OldEng"}
    )
    mock_data_service.add_entry("ppm", existing_ppm_data) # This will add calculated dates

    entry_before_update = mock_data_service.get_entry("ppm", "EXIST_PPM01_NEW")
    assert entry_before_update["MODEL"] == "OldModel"
    assert entry_before_update["PPM_Q_I"]["engineer"] == "OldEng"
    assert entry_before_update["PPM_Q_I"]["quarter_date"] == "01/04/2023"

    # CSV data to update the existing entry
    update_csv_row = {
        "EQUIPMENT": entry_before_update["EQUIPMENT"], "MODEL": "NewModelPPM_NEW", "Name": entry_before_update["Name"],
        "SERIAL": "EXIST_PPM01_NEW", "MANUFACTURER": entry_before_update["MANUFACTURER"],
        "Department": entry_before_update["Department"], "LOG_NO": entry_before_update["LOG_NO"],
        "Installation_Date": "01/02/2023", # New Install Date -> new quarter dates
        "Warranty_End": entry_before_update["Warranty_End"], "Status": "", "OCM": "",
        "Q1_Engineer": "UpdatedEng", "Q2_Engineer": "NewQ2Eng", "Q3_Engineer": "", "Q4_Engineer": ""
    }
    csv_content = create_csv_string(PPM_CSV_IMPORT_HEADERS_NEW, [update_csv_row])
    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))

    assert result["added_count"] == 0
    assert result["updated_count"] == 1, f"Errors: {result['errors']}"
    assert result["skipped_count"] == 0
    assert not result["errors"]

    updated_entry_db = mock_data_service.get_entry("ppm", "EXIST_PPM01_NEW")
    assert updated_entry_db["MODEL"] == "NewModelPPM_NEW"
    assert updated_entry_db["PPM_Q_I"]["engineer"] == "UpdatedEng"
    assert updated_entry_db["PPM_Q_II"]["engineer"] == "NewQ2Eng"
    assert updated_entry_db["Installation_Date"] == "01/02/2023"
    assert updated_entry_db["PPM_Q_I"]["quarter_date"] == "01/05/2023" # Recalculated from new Installation_Date
    assert updated_entry_db["NO"] == 1 # Ensure NO is preserved


def test_import_data_invalid_rows_ppm_new_format(mock_data_service):
    # Valid entry, entry with bad date (optional, so should be None), entry with missing required field
    valid_row = {
        "EQUIPMENT": "PPM Valid", "MODEL": "V1", "SERIAL": "VALID_IMP01_NEW", "MANUFACTURER": "M",
        "Department": "D", "LOG_NO": "L1", "Installation_Date": "01/01/2023",
        "Q1_Engineer": "E"
    }
    # Installation_Date here is not DD/MM/YYYY, Pydantic validator on PPMEntry should catch this if not empty.
    # If empty, it's None. If "invalid-date", the model's validator will raise error.
    # DataService import logic for PPM now sets empty optional dates to None *before* Pydantic.
    # So, a "bad date" means an *invalidly formatted non-empty* date.
    ppm_bad_date_row = {**valid_row, "SERIAL": "BAD_DATE01_NEW", "Installation_Date": "32/13/2023"}

    ppm_missing_req_field_row = {**valid_row, "SERIAL": "MISSING01_NEW"}
    del ppm_missing_req_field_row["EQUIPMENT"]

    csv_rows = [valid_row, ppm_bad_date_row, ppm_missing_req_field_row]
    csv_content = create_csv_string(PPM_CSV_IMPORT_HEADERS_NEW, csv_rows)
    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))

    assert result["added_count"] == 1 # Only valid_ppm
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 2, f"Errors: {result['errors']}"
    assert len(result["errors"]) == 2
    # Error for bad_date_row: Pydantic validation error on Installation_Date
    assert "VALID_IMP01_NEW" == mock_data_service.get_entry("ppm", "VALID_IMP01_NEW")["SERIAL"]
    assert "BAD_DATE01_NEW" in result["errors"][0] # Error message includes SERIAL
    assert "Invalid date format for Installation_Date" in result["errors"][0] # Model validation error

    # Error for missing_req_field_row: Pydantic validation error on EQUIPMENT
    assert "MISSING01_NEW" in result["errors"][1]
    assert "Field required" in result["errors"][1] # Pydantic's message for missing field

    assert mock_data_service.get_entry("ppm", "VALID_IMP01_NEW") is not None
    assert mock_data_service.get_entry("ppm", "BAD_DATE01_NEW") is None
    assert mock_data_service.get_entry("ppm", "MISSING01_NEW") is None


def test_import_data_empty_csv_ppm_new_format(mock_data_service):
    csv_content = create_csv_string(PPM_CSV_IMPORT_HEADERS_NEW, []) # Only headers
    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))
    assert result["added_count"] == 0
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 0
    assert not result["errors"]

    # Test with completely empty file (no headers)
    result_empty_file = mock_data_service.import_data("ppm", io.StringIO(""))
    assert result_empty_file["added_count"] == 0
    assert "Import Error: The uploaded CSV file is empty." in result_empty_file["errors"]


def test_import_data_bad_headers_ppm_new_format(mock_data_service):
    bad_headers = ["SERIAL", "MODEL", "Q1_Engineer_WRONG_NAME"] # Missing required EQUIPMENT, wrong Q eng name
    row_data = [{"SERIAL": "TestBadHeader", "MODEL": "TestModel", "Q1_Engineer_WRONG_NAME": "EngX"}]
    csv_content = create_csv_string(bad_headers, row_data)

    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))
    assert result["skipped_count"] == 1
    assert "Validation error" in result["errors"][0]
    assert "Field required" in result["errors"][0] # For EQUIPMENT


# --- Tests for export_data ---
def test_export_data_ppm_new_format(mock_data_service, mocker):
    # Mock today for consistent quarter date calculation by the service
    fixed_today = date(2023, 1, 10)
    mocker.patch('app.services.data_service.datetime').today.return_value = fixed_today

    # Prepare data that would be in the system (i.e., with quarter_dates calculated)
    ppm1_input = create_valid_ppm_dict(
        SERIAL="EXP_PPM01_NEW",
        Installation_Date="01/10/2022", # Q1=01/01/2023
        PPM_Q_I={"engineer": "EngExportQ1"},
        PPM_Q_II={"engineer": "EngExportQ2"}
    )
    ppm2_input = create_valid_ppm_dict(
        SERIAL="EXP_PPM02_NEW",
        Name=None, # Optional name not provided
        Installation_Date=None, # Q1 from fixed_today = 10/04/2023
        PPM_Q_IV={"engineer": "EngExportQ4"}
    )
    mock_data_service.add_entry("ppm", ppm1_input)
    mock_data_service.add_entry("ppm", ppm2_input)

    csv_output_string = mock_data_service.export_data("ppm")
    csv_reader = csv.DictReader(io.StringIO(csv_output_string))
    exported_rows = list(csv_reader)

    assert len(exported_rows) == 2

    # Expected headers for new PPM export format
    PPM_EXPORT_HEADERS_NEW = [
        'NO', 'EQUIPMENT', 'MODEL', 'Name', 'SERIAL', 'MANUFACTURER',
        'Department', 'LOG_NO', 'Installation_Date', 'Warranty_End', 'OCM', 'Status',
        'Q1_Date', 'Q1_Engineer', 'Q2_Date', 'Q2_Engineer',
        'Q3_Date', 'Q3_Engineer', 'Q4_Date', 'Q4_Engineer'
    ]
    assert csv_reader.fieldnames == PPM_EXPORT_HEADERS_NEW

    # Verify row 1 (EXP_PPM01_NEW)
    row1 = next(r for r in exported_rows if r["SERIAL"] == "EXP_PPM01_NEW")
    assert row1["Installation_Date"] == "01/10/2022"
    assert row1["Q1_Date"] == "01/01/2023"
    assert row1["Q1_Engineer"] == "EngExportQ1"
    assert row1["Q2_Date"] == "01/04/2023"
    assert row1["Q2_Engineer"] == "EngExportQ2"
    assert row1["Q3_Engineer"] == "" # Default from create_valid_ppm_dict

    # Verify row 2 (EXP_PPM02_NEW)
    row2 = next(r for r in exported_rows if r["SERIAL"] == "EXP_PPM02_NEW")
    assert row2["Name"] == "" # Optional None field exported as empty
    assert row2["Installation_Date"] == "" # Was None, exported as empty
    assert row2["Q1_Date"] == "10/04/2023" # Calculated from fixed_today
    assert row2["Q1_Engineer"] == ""       # Default
    assert row2["Q4_Engineer"] == "EngExportQ4"


def test_export_data_ocm(mock_data_service): # Keep OCM test as is
    ocm1 = create_valid_ocm_dict(SERIAL="EXP_OCM01")
    mock_data_service.add_entry("ocm", ocm1)
    csv_output_string = mock_data_service.export_data("ocm")
    csv_reader = csv.DictReader(io.StringIO(csv_output_string))
    exported_rows = list(csv_reader)

    assert len(exported_rows) == 1
    assert exported_rows[0]["SERIAL"] == "EXP_OCM01"
    assert exported_rows[0]["Installation_Date"] == ocm1["Installation_Date"]
    expected_headers = ['NO'] + [h for h in OCM_MODEL_FIELDS if h != 'NO']
    assert csv_reader.fieldnames == expected_headers


def test_export_data_empty(mock_data_service):
    csv_output_string = mock_data_service.export_data("ppm")
    # Current export returns "" for no data.
    # A CSV with only headers might be an alternative.
    # Based on current DataService: if not data: return ""
    assert csv_output_string == ""

    # If it were to return headers only:
    # if not csv_output_string: pytest.fail("CSV output is empty for no data, expected headers.")
    # csv_reader = csv.DictReader(io.StringIO(csv_output_string))
    # assert csv_reader.fieldnames is not None # Check headers exist
    # assert len(list(csv_reader)) == 0 # No data rows


# Need to import csv for helper
import csv
