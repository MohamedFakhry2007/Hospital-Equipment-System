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
def create_valid_ppm_dict(mfg_serial="PPM_SN001", equipment="PPM Device", model="PPM1000", **kwargs):
    base_data = {
        "EQUIPMENT": equipment,
        "MODEL": model,
        "Name": f"{equipment} {model}",
        "MFG_SERIAL": mfg_serial,
        "MANUFACTURER": "PPM Manufacturer",
        "Department": "PPM Department",
        "LOG_NO": "PPM_LOG001",
        "Installation_Date": "01/01/2023",
        "Warranty_End": "01/01/2025",
        "Eng1": "Eng PPM1", "Eng2": "Eng PPM2", "Eng3": "", "Eng4": "",
        "Status": "Upcoming", # Will be recalculated by add/update unless specified
        "PPM_Q_I": {"engineer": "Q1 Engineer"},
        "PPM_Q_II": {"engineer": "Q2 Engineer"},
        "PPM_Q_III": {"engineer": ""},
        "PPM_Q_IV": {"engineer": ""},
    }
    base_data.update(kwargs)
    return base_data

def create_valid_ocm_dict(mfg_serial="OCM_SN001", equipment="OCM Device", model="OCM1000", **kwargs):
    base_data = {
        "EQUIPMENT": equipment,
        "MODEL": model,
        "Name": f"{equipment} {model}",
        "MFG_SERIAL": mfg_serial,
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
    data = create_valid_ppm_dict(MFG_SERIAL="PPM_S001")
    added_entry = mock_data_service.add_entry("ppm", data)

    assert added_entry["MFG_SERIAL"] == "PPM_S001"
    assert added_entry["NO"] == 1
    # Status calculation for PPM is basic: "Upcoming" if not all EngX filled, "Maintained" if all filled.
    # For default create_valid_ppm_dict, Eng3 and Eng4 are empty.
    assert added_entry["Status"] == "Upcoming"

    all_entries = mock_data_service.get_all_entries("ppm")
    assert len(all_entries) == 1
    # Compare relevant fields, NO and Status are auto-set
    retrieved_entry = mock_data_service.get_entry("ppm", "PPM_S001")
    assert retrieved_entry["MODEL"] == data["MODEL"]


def test_add_ocm_entry(mock_data_service):
    """Test adding a new OCM entry."""
    data = create_valid_ocm_dict(MFG_SERIAL="OCM_S001", Next_Maintenance="01/01/2025") # Future date
    added_entry = mock_data_service.add_entry("ocm", data)
    assert added_entry["MFG_SERIAL"] == "OCM_S001"
    assert added_entry["NO"] == 1
    assert added_entry["Status"] == "Upcoming" # Based on Next_Maintenance being in future
    all_entries = mock_data_service.get_all_entries("ocm")
    assert len(all_entries) == 1


def test_add_duplicate_mfg_serial(mock_data_service):
    """Test adding an entry with a duplicate MFG_SERIAL."""
    data1 = create_valid_ppm_dict(MFG_SERIAL="DUP001")
    mock_data_service.add_entry("ppm", data1)

    data2 = create_valid_ppm_dict(MFG_SERIAL="DUP001", EQUIPMENT="Another Device")
    with pytest.raises(ValueError, match="Duplicate MFG_SERIAL detected: DUP001"):
        mock_data_service.add_entry("ppm", data2)


def test_update_ppm_entry(mock_data_service):
    """Test updating an existing PPM entry."""
    original_data = create_valid_ppm_dict(MFG_SERIAL="PPM_U001", Eng1="Done", Eng2="Done", Eng3="", Eng4="")
    mock_data_service.add_entry("ppm", original_data)
    # Original status should be "Upcoming"

    update_payload = {"Eng3": "Now Done", "Eng4": "Also Done", "MODEL": "PPM1000-rev2"}
    # Create a full dict for update, DataService.update_entry expects all required fields
    updated_data_full = original_data.copy()
    updated_data_full.update(update_payload)

    returned_updated_entry = mock_data_service.update_entry("ppm", "PPM_U001", updated_data_full)

    assert returned_updated_entry["MODEL"] == "PPM1000-rev2"
    assert returned_updated_entry["Eng3"] == "Now Done"
    # Now all Eng1-4 are filled, status should be "Maintained"
    assert returned_updated_entry["Status"] == "Maintained"
    assert returned_updated_entry["NO"] == 1 # NO should be preserved


def test_update_ocm_next_maintenance_to_overdue(mock_data_service, mocker):
    """Test OCM entry status changes to Overdue when Next_Maintenance is updated to past."""
    # Mock current date to be fixed
    fixed_now = datetime(2024, 3, 15) # March 15, 2024
    mocker.patch('app.services.data_service.datetime', now=lambda: fixed_now)

    original_data = create_valid_ocm_dict(MFG_SERIAL="OCM_U002", Next_Maintenance="01/04/2024") # Upcoming
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
    update_data = create_valid_ppm_dict(MFG_SERIAL="NONEXISTENT")
    with pytest.raises(KeyError, match="Entry with MFG_SERIAL 'NONEXISTENT' not found for update."):
        mock_data_service.update_entry("ppm", "NONEXISTENT", update_data)


def test_update_mfg_serial_not_allowed(mock_data_service):
    """Test attempting to update MFG_SERIAL."""
    original_data = create_valid_ppm_dict(MFG_SERIAL="SERIAL_ORIG")
    mock_data_service.add_entry("ppm", original_data)

    update_data = original_data.copy()
    update_data["MFG_SERIAL"] = "SERIAL_NEW" # Attempting to change MFG_SERIAL

    with pytest.raises(ValueError, match="Cannot change MFG_SERIAL"):
        mock_data_service.update_entry("ppm", "SERIAL_ORIG", update_data)


def test_delete_entry(mock_data_service):
    """Test deleting an existing entry and reindexing."""
    data1 = create_valid_ppm_dict(MFG_SERIAL="DEL_S001")
    data2 = create_valid_ppm_dict(MFG_SERIAL="DEL_S002")
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
    data1 = create_valid_ppm_dict(MFG_SERIAL="GETALL_S001")
    data2 = create_valid_ppm_dict(MFG_SERIAL="GETALL_S002")
    mock_data_service.add_entry("ppm", data1)
    mock_data_service.add_entry("ppm", data2)

    all_entries = mock_data_service.get_all_entries("ppm")
    assert len(all_entries) == 2
    # Entries in all_entries will have 'NO' and calculated 'Status'
    # We need to compare based on a common key like MFG_SERIAL
    mfg_serials_retrieved = {e["MFG_SERIAL"] for e in all_entries}
    assert "GETALL_S001" in mfg_serials_retrieved
    assert "GETALL_S002" in mfg_serials_retrieved


def test_get_entry(mock_data_service):
    """Test getting a specific entry by MFG_SERIAL."""
    data = create_valid_ocm_dict(MFG_SERIAL="GET_S001")
    mock_data_service.add_entry("ocm", data)

    retrieved_entry = mock_data_service.get_entry("ocm", "GET_S001")
    assert retrieved_entry is not None
    assert retrieved_entry["MODEL"] == data["MODEL"]
    assert retrieved_entry["NO"] == 1


def test_get_nonexistent_entry(mock_data_service):
    """Test getting a non-existent entry."""
    assert mock_data_service.get_entry("ppm", "NONEXISTENT_GET") is None


# Tests for ensure_unique_mfg_serial and reindex are implicitly covered by add/delete tests.

# --- New tests for load_data ---
def test_load_data_valid_ppm(mock_data_service, tmp_path):
    ppm_file = tmp_path / "test_ppm.json"
    valid_entry_dict = create_valid_ppm_dict(MFG_SERIAL="LD_PPM01")
    # Manually save data to simulate existing file
    with open(ppm_file, 'w') as f:
        json.dump([valid_entry_dict], f)

    loaded_data = mock_data_service.load_data("ppm")
    assert len(loaded_data) == 1
    assert loaded_data[0]["MFG_SERIAL"] == "LD_PPM01"

def test_load_data_valid_ocm(mock_data_service, tmp_path):
    ocm_file = tmp_path / "test_ocm.json"
    valid_entry_dict = create_valid_ocm_dict(MFG_SERIAL="LD_OCM01")
    with open(ocm_file, 'w') as f:
        json.dump([valid_entry_dict], f)

    loaded_data = mock_data_service.load_data("ocm")
    assert len(loaded_data) == 1
    assert loaded_data[0]["MFG_SERIAL"] == "LD_OCM01"

def test_load_data_skips_invalid_entries(mock_data_service, tmp_path, caplog):
    ppm_file = tmp_path / "test_ppm.json"
    valid_entry = create_valid_ppm_dict(MFG_SERIAL="VALID01")
    invalid_entry_dict = create_valid_ppm_dict(MFG_SERIAL="INVALID01")
    invalid_entry_dict["Installation_Date"] = "invalid-date-format" # Invalid data

    with open(ppm_file, 'w') as f:
        json.dump([valid_entry, invalid_entry_dict], f)

    loaded_data = mock_data_service.load_data("ppm")
    assert len(loaded_data) == 1 # Should skip the invalid one
    assert loaded_data[0]["MFG_SERIAL"] == "VALID01"
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
        f.write("[{'MFG_SERIAL': 'MALFORMED'}]") # Malformed JSON (single quotes)

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
    entry1 = create_valid_ppm_dict(MFG_SERIAL="SAVE_PPM01")
    entry2 = create_valid_ppm_dict(MFG_SERIAL="SAVE_PPM02")
    data_to_save = [entry1, entry2]

    mock_data_service.save_data(data_to_save, "ppm")

    with open(ppm_file, 'r') as f:
        saved_data_on_disk = json.load(f)

    assert len(saved_data_on_disk) == 2
    assert saved_data_on_disk[0]["MFG_SERIAL"] == "SAVE_PPM01"
    assert saved_data_on_disk[1]["MFG_SERIAL"] == "SAVE_PPM02"

def test_save_data_ocm(mock_data_service, tmp_path):
    ocm_file = tmp_path / "test_ocm.json"
    entry1 = create_valid_ocm_dict(MFG_SERIAL="SAVE_OCM01")
    data_to_save = [entry1]

    mock_data_service.save_data(data_to_save, "ocm")

    with open(ocm_file, 'r') as f:
        saved_data_on_disk = json.load(f)
    assert len(saved_data_on_disk) == 1
    assert saved_data_on_disk[0]["MFG_SERIAL"] == "SAVE_OCM01"


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
        "MFG_SERIAL": "TestOCMStatus"
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


@pytest.mark.parametrize("eng_fields, expected_status", [
    ({"Eng1": "Done", "Eng2": "Done", "Eng3": "Done", "Eng4": "Done"}, "Maintained"),
    ({"Eng1": "Done", "Eng2": "Done", "Eng3": "Done", "Eng4": ""}, "Upcoming"),
    ({"Eng1": "Done", "Eng2": "", "Eng3": "", "Eng4": ""}, "Upcoming"),
    ({"Eng1": "", "Eng2": "", "Eng3": "", "Eng4": ""}, "Upcoming"),
])
def test_calculate_status_ppm(mock_data_service, eng_fields, expected_status):
    # PPM status calculation is currently basic, not date-dependent in `calculate_status`
    ppm_entry_data = {**eng_fields, "MFG_SERIAL": "TestPPMStatus"}
    status = mock_data_service.calculate_status(ppm_entry_data, "ppm")
    assert status == expected_status

# --- Tests for add_entry with status ---
def test_add_ppm_entry_calculates_status(mock_data_service):
    data_no_status = create_valid_ppm_dict(MFG_SERIAL="PPM_ADD_S001", Eng1="X", Eng2="X", Eng3="X", Eng4="X")
    del data_no_status["Status"] # Remove status so it's calculated
    added_entry = mock_data_service.add_entry("ppm", data_no_status)
    assert added_entry["Status"] == "Maintained"

    data_partial_eng = create_valid_ppm_dict(MFG_SERIAL="PPM_ADD_S002", Eng1="X", Eng2="", Eng3="", Eng4="")
    del data_partial_eng["Status"]
    added_entry_2 = mock_data_service.add_entry("ppm", data_partial_eng)
    assert added_entry_2["Status"] == "Upcoming"

def test_add_ocm_entry_calculates_status(mock_data_service, mocker):
    fixed_today = date(2024, 3, 15)
    mocker.patch('app.services.data_service.datetime', now=lambda: datetime(fixed_today.year, fixed_today.month, fixed_today.day))

    data_overdue = create_valid_ocm_dict(MFG_SERIAL="OCM_ADD_S001", Next_Maintenance="01/01/2024", Service_Date=None)
    if "Status" in data_overdue: del data_overdue["Status"]
    added_entry = mock_data_service.add_entry("ocm", data_overdue)
    assert added_entry["Status"] == "Overdue"

    data_upcoming = create_valid_ocm_dict(MFG_SERIAL="OCM_ADD_S002", Next_Maintenance="01/06/2024", Service_Date=None)
    if "Status" in data_upcoming: del data_upcoming["Status"]
    added_entry_2 = mock_data_service.add_entry("ocm", data_upcoming)
    assert added_entry_2["Status"] == "Upcoming"

# --- Tests for update_entry with status ---
def test_update_ppm_entry_recalculates_status(mock_data_service):
    ppm_data = create_valid_ppm_dict(MFG_SERIAL="PPM_UPD_S001", Eng1="X", Eng2="", Eng3="", Eng4="") # Initially Upcoming
    mock_data_service.add_entry("ppm", ppm_data)

    update_payload = ppm_data.copy() # Start with full original data
    update_payload["Eng2"] = "X"
    update_payload["Eng3"] = "X"
    update_payload["Eng4"] = "X" # Now all Eng fields will be filled
    if "Status" in update_payload: del update_payload["Status"] # Ensure status is recalculated

    updated_entry = mock_data_service.update_entry("ppm", "PPM_UPD_S001", update_payload)
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
    ppm_entry_1 = create_valid_ppm_dict(MFG_SERIAL="IMP_PPM01", Status="Upcoming") # Explicit status
    ppm_entry_2 = create_valid_ppm_dict(MFG_SERIAL="IMP_PPM02", Eng1="E1", Eng2="E2", Eng3="E3", Eng4="E4") # All eng filled
    # For import, QuarterData should be represented by simple engineer string if header is e.g. PPM_Q_I
    # The import_data logic converts this string to {"engineer": "string"}
    csv_rows = [
        {k: (v["engineer"] if isinstance(v, dict) else v) for k, v in ppm_entry_1.items() if k != 'NO'},
        {k: (v["engineer"] if isinstance(v, dict) else v) for k, v in ppm_entry_2.items() if k != 'NO'}
    ]
    # Status will be recalculated if not valid, or taken if valid.
    # For ppm_entry_2, status will be "Maintained" after calculation if not provided or invalid.
    del csv_rows[1]["Status"] # Let status be calculated for the second entry

    csv_content = create_csv_string(PPM_CSV_IMPORT_HEADERS, csv_rows)

    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))

    assert result["added_count"] == 2
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 0
    assert not result["errors"]

    entry1_db = mock_data_service.get_entry("ppm", "IMP_PPM01")
    assert entry1_db is not None
    assert entry1_db["Status"] == "Upcoming" # Used provided valid status

    entry2_db = mock_data_service.get_entry("ppm", "IMP_PPM02")
    assert entry2_db is not None
    assert entry2_db["Status"] == "Maintained" # Recalculated


def test_import_data_new_ocm_entries(mock_data_service, mocker):
    fixed_today = date(2024, 3, 15)
    mocker.patch('app.services.data_service.datetime', now=lambda: datetime(fixed_today.year, fixed_today.month, fixed_today.day))

    ocm_entry_1 = create_valid_ocm_dict(MFG_SERIAL="IMP_OCM01", Next_Maintenance="01/01/2024") # Overdue
    ocm_entry_2 = create_valid_ocm_dict(MFG_SERIAL="IMP_OCM02", Next_Maintenance="01/06/2024") # Upcoming
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
    existing_ppm = create_valid_ppm_dict(MFG_SERIAL="EXIST_PPM01", MODEL="OldModel")
    mock_data_service.add_entry("ppm", existing_ppm)
    assert mock_data_service.get_entry("ppm", "EXIST_PPM01")["MODEL"] == "OldModel"

    # CSV data to update the existing entry
    update_csv_row_dict = create_valid_ppm_dict(MFG_SERIAL="EXIST_PPM01", MODEL="NewModelPPM")
    # Flatten QuarterData for CSV representation
    update_csv_row_flat = {k: (v["engineer"] if isinstance(v, dict) else v) for k,v in update_csv_row_dict.items() if k != 'NO'}

    csv_content = create_csv_string(PPM_CSV_IMPORT_HEADERS, [update_csv_row_flat])
    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))

    assert result["added_count"] == 0
    assert result["updated_count"] == 1
    assert result["skipped_count"] == 0
    assert not result["errors"]

    updated_entry_db = mock_data_service.get_entry("ppm", "EXIST_PPM01")
    assert updated_entry_db["MODEL"] == "NewModelPPM"
    assert updated_entry_db["NO"] == 1 # Ensure NO is preserved


def test_import_data_invalid_rows(mock_data_service):
    # Valid entry, entry with bad date, entry with missing required field
    valid_ppm = create_valid_ppm_dict(MFG_SERIAL="VALID_IMP01")
    ppm_bad_date = create_valid_ppm_dict(MFG_SERIAL="BAD_DATE01", Installation_Date="32/13/2023")
    ppm_missing_field = create_valid_ppm_dict(MFG_SERIAL="MISSING01")
    del ppm_missing_field["EQUIPMENT"] # EQUIPMENT is a required field

    csv_rows = [
        {k: (v["engineer"] if isinstance(v, dict) else v) for k,v in valid_ppm.items() if k != 'NO'},
        {k: (v["engineer"] if isinstance(v, dict) else v) for k,v in ppm_bad_date.items() if k != 'NO'},
        {k: (v["engineer"] if isinstance(v, dict) else v) for k,v in ppm_missing_field.items() if k != 'NO'},
    ]
    csv_content = create_csv_string(PPM_CSV_IMPORT_HEADERS, csv_rows)
    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))

    assert result["added_count"] == 1 # Only valid_ppm
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 2
    assert len(result["errors"]) == 2
    assert "Invalid date format for Installation_Date" in result["errors"][0]
    # The Pydantic error for missing field will be caught by the model validation.
    assert "Validation error" in result["errors"][1]
    assert "Field required" in result["errors"][1] # Pydantic's message for missing field

    assert mock_data_service.get_entry("ppm", "VALID_IMP01") is not None
    assert mock_data_service.get_entry("ppm", "BAD_DATE01") is None
    assert mock_data_service.get_entry("ppm", "MISSING01") is None


def test_import_data_empty_csv(mock_data_service):
    csv_content = create_csv_string(PPM_CSV_IMPORT_HEADERS, []) # Only headers
    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))
    assert result["added_count"] == 0
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 0
    assert not result["errors"]

    # Test with completely empty file (no headers)
    result_empty_file = mock_data_service.import_data("ppm", io.StringIO(""))
    assert result_empty_file["added_count"] == 0
    assert "Import Error: The uploaded CSV file is empty." in result_empty_file["errors"]


def test_import_data_bad_headers(mock_data_service):
    # CSV with missing or incorrect headers.
    # The current pandas based import might still try to process if some headers match,
    # or might raise error if critical headers for model are missing.
    # Pydantic validation will catch missing required fields.
    bad_headers = ["MFG_SERIAL", "MODEL", "WRONG_HEADER_FOR_EQUIPMENT"]
    row_data = [{"MFG_SERIAL": "TestBadHeader", "MODEL": "TestModel", "WRONG_HEADER_FOR_EQUIPMENT": "SomeEquip"}]
    csv_content = create_csv_string(bad_headers, row_data)

    result = mock_data_service.import_data("ppm", io.StringIO(csv_content))
    assert result["skipped_count"] == 1
    assert "Validation error" in result["errors"][0] # Pydantic will complain about missing EQUIPMENT
    assert "Field required" in result["errors"][0]


# --- Tests for export_data ---
def test_export_data_ppm(mock_data_service):
    ppm1 = create_valid_ppm_dict(MFG_SERIAL="EXP_PPM01", Eng1="E1", PPM_Q_I={"engineer": "Q1Eng"})
    ppm2 = create_valid_ppm_dict(MFG_SERIAL="EXP_PPM02", Name=None) # Optional name not provided
    mock_data_service.add_entry("ppm", ppm1)
    mock_data_service.add_entry("ppm", ppm2)

    csv_output_string = mock_data_service.export_data("ppm")

    # Parse the CSV string back to check content
    csv_reader = csv.DictReader(io.StringIO(csv_output_string))
    exported_rows = list(csv_reader)

    assert len(exported_rows) == 2
    assert exported_rows[0]["MFG_SERIAL"] == "EXP_PPM01"
    assert exported_rows[0]["Eng1"] == "E1"
    assert exported_rows[0]["PPM_Q_I"] == "Q1Eng" # Check flattened QuarterData
    assert exported_rows[1]["MFG_SERIAL"] == "EXP_PPM02"
    assert exported_rows[1]["Name"] == "" # Optional None field exported as empty string by default DictWriter behavior

    # Check headers - NO should be first
    expected_headers = ['NO'] + [h for h in PPM_MODEL_FIELDS if h != 'NO']
    assert csv_reader.fieldnames == expected_headers


def test_export_data_ocm(mock_data_service):
    ocm1 = create_valid_ocm_dict(MFG_SERIAL="EXP_OCM01")
    mock_data_service.add_entry("ocm", ocm1)
    csv_output_string = mock_data_service.export_data("ocm")
    csv_reader = csv.DictReader(io.StringIO(csv_output_string))
    exported_rows = list(csv_reader)

    assert len(exported_rows) == 1
    assert exported_rows[0]["MFG_SERIAL"] == "EXP_OCM01"
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
