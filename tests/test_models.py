import pytest
from pydantic import ValidationError

from app.models.ppm import PPMEntry, QuarterData
from app.models.ocm import OCMEntry


# Test data for PPMEntry
valid_ppm_data = {
    "EQUIPMENT": "Test Equipment",
    "MODEL": "Test Model",
    "Name": "Optional Name",
    "SERIAL": "SN123",
    "MANUFACTURER": "Test Manufacturer",
    "Department": "Test Department",
    "LOG_NO": "Log001",
    "Installation_Date": "01/01/2023",
    "Warranty_End": "01/01/2025",
    # Eng1-Eng4 removed
    "Status": "Upcoming",
    "PPM_Q_I": {"engineer": "Eng Q1", "quarter_date": "01/04/2023"},
    "PPM_Q_II": {"engineer": "Eng Q2", "quarter_date": "01/07/2023"},
    "PPM_Q_III": {"engineer": "Eng Q3", "quarter_date": "01/10/2023"},
    "PPM_Q_IV": {"engineer": "Eng Q4", "quarter_date": "01/01/2024"},
}

# Test data for OCMEntry
valid_ocm_data = {
    "EQUIPMENT": "OCM Equipment",
    "MODEL": "OCM Model",
    "Name": "Optional OCM Name",
    "SERIAL": "SN456",
    "MANUFACTURER": "OCM Manufacturer",
    "Department": "OCM Department",
    "LOG_NO": "Log002",
    "Installation_Date": "01/02/2023",
    "Warranty_End": "01/02/2025",
    "Service_Date": "01/06/2024",
    "Next_Maintenance": "01/06/2025",
    "ENGINEER": "Engineer X",
    "Status": "Maintained",
}


class TestPPMEntry:
    def test_successful_creation(self):
        entry = PPMEntry(**valid_ppm_data)
        assert entry.EQUIPMENT == valid_ppm_data["EQUIPMENT"]
        assert entry.MODEL == valid_ppm_data["MODEL"]
        assert entry.Name == valid_ppm_data["Name"]
        assert entry.Status == "Upcoming"
        assert entry.PPM_Q_I.engineer == "Eng Q1"
        assert entry.PPM_Q_I.quarter_date == "01/04/2023"

    def test_optional_and_invalid_date_formats(self):
        # Test valid None and empty string for optional dates
        data_none_install = valid_ppm_data.copy()
        data_none_install["Installation_Date"] = None
        entry_none_install = PPMEntry(**data_none_install)
        assert entry_none_install.Installation_Date is None

        data_empty_warranty = valid_ppm_data.copy()
        data_empty_warranty["Warranty_End"] = ""
        entry_empty_warranty = PPMEntry(**data_empty_warranty)
        assert entry_empty_warranty.Warranty_End == "" # Or None, depending on Pydantic coercion for Optional[str] with allow_empty_str

        # Test invalid format for Installation_Date
        data_invalid_install = valid_ppm_data.copy()
        data_invalid_install["Installation_Date"] = "2023-01-01" # Invalid format
        with pytest.raises(ValidationError) as excinfo_install:
            PPMEntry(**data_invalid_install)
        assert "Installation_Date" in str(excinfo_install.value)
        assert "Invalid date format" in str(excinfo_install.value)

        # Test invalid format for Warranty_End
        data_invalid_warranty = valid_ppm_data.copy()
        data_invalid_warranty["Warranty_End"] = "01-01-2025" # Invalid format
        with pytest.raises(ValidationError) as excinfo_warranty:
            PPMEntry(**data_invalid_warranty)
        assert "Warranty_End" in str(excinfo_warranty.value)
        assert "Invalid date format" in str(excinfo_warranty.value)


    def test_empty_required_fields(self):
        # Eng1-4 removed, Installation_Date and Warranty_End are optional
        required_fields = ["EQUIPMENT", "MODEL", "SERIAL", "MANUFACTURER", "Department", "LOG_NO"]
        for field in required_fields:
            data = valid_ppm_data.copy()
            data[field] = "" # Empty string
            with pytest.raises(ValidationError) as excinfo:
                PPMEntry(**data)
            assert field in str(excinfo.value) # Check that the error message mentions the field

    def test_invalid_status(self):
        data = valid_ppm_data.copy()
        data["Status"] = "InvalidStatus"
        with pytest.raises(ValidationError):
            PPMEntry(**data)

    def test_quarter_data_empty_engineer(self):
        data = valid_ppm_data.copy()
        data["PPM_Q_I"] = {"engineer": " "} # Engineer field with only whitespace
        # Based on QuarterData validator: `if v is None or not v.strip(): return None`
        # So, " " becomes None, which is valid.
        entry = PPMEntry(**data)
        assert entry.PPM_Q_I.engineer is None

    def test_quarter_data_structure(self):
        # Test successful creation with full QuarterData
        data = valid_ppm_data.copy()
        data["PPM_Q_II"] = {"engineer": "EngTest", "quarter_date": "15/05/2023"}
        entry = PPMEntry(**data)
        assert entry.PPM_Q_II.engineer == "EngTest"
        assert entry.PPM_Q_II.quarter_date == "15/05/2023"

        # Test with engineer being None in QuarterData
        data["PPM_Q_III"] = {"engineer": None, "quarter_date": "15/08/2023"}
        entry = PPMEntry(**data)
        assert entry.PPM_Q_III.engineer is None
        assert entry.PPM_Q_III.quarter_date == "15/08/2023"

        # Test with quarter_date being None
        data["PPM_Q_IV"] = {"engineer": "EngTestQ4", "quarter_date": None}
        entry = PPMEntry(**data)
        assert entry.PPM_Q_IV.engineer == "EngTestQ4"
        assert entry.PPM_Q_IV.quarter_date is None

        # Test with both being None
        data["PPM_Q_I"] = {"engineer": None, "quarter_date": None}
        entry = PPMEntry(**data)
        assert entry.PPM_Q_I.engineer is None
        assert entry.PPM_Q_I.quarter_date is None

        # Test with only engineer provided (quarter_date will be None)
        data["PPM_Q_II"] = {"engineer": "OnlyEng"}
        entry = PPMEntry(**data)
        assert entry.PPM_Q_II.engineer == "OnlyEng"
        assert entry.PPM_Q_II.quarter_date is None

        # Test with only quarter_date provided (engineer will be None)
        # This case {"quarter_date": "date"} is not how QuarterData is defined if engineer is required
        # but QuarterData has engineer: Optional[str]=None. So this is valid.
        data["PPM_Q_III"] = {"quarter_date": "A_Date_Str"}
        entry = PPMEntry(**data)
        assert entry.PPM_Q_III.engineer is None
        assert entry.PPM_Q_III.quarter_date == "A_Date_Str"


class TestOCMEntry:
    def test_successful_creation(self):
        entry = OCMEntry(**valid_ocm_data)
        assert entry.EQUIPMENT == valid_ocm_data["EQUIPMENT"]
        assert entry.MODEL == valid_ocm_data["MODEL"]
        assert entry.Name == valid_ocm_data["Name"]
        assert entry.Status == "Maintained"
        assert entry.ENGINEER == "Engineer X"

    def test_invalid_date_format(self):
        date_fields = ["Installation_Date", "Warranty_End", "Service_Date", "Next_Maintenance"]
        for field in date_fields:
            data = valid_ocm_data.copy()
            data[field] = "2023-01-01"  # Invalid format
            with pytest.raises(ValidationError):
                OCMEntry(**data)

    def test_empty_required_fields(self):
        required_fields = ["EQUIPMENT", "MODEL", "SERIAL", "MANUFACTURER", "Department", "LOG_NO", "ENGINEER"]
        for field in required_fields:
            data = valid_ocm_data.copy()
            data[field] = ""
            with pytest.raises(ValidationError):
                OCMEntry(**data)

    def test_invalid_status(self):
        data = valid_ocm_data.copy()
        data["Status"] = "NonExistentStatus"
        with pytest.raises(ValidationError):
            OCMEntry(**data)


# Test data for Training model
new_format_training_data_valid = {
    "id": 1,
    "employee_id": "E1001",
    "name": "John Doe",
    "department": "Production A",
    "machine_trainer_assignments": [
        {"machine": "CNC Mill", "trainer": "Alice"},
        {"machine": "Lathe X1000", "trainer": "Bob"}
    ],
    "last_trained_date": "2023-01-15",
    "next_due_date": "2024-01-15"
}

old_format_training_data_str_machines = {
    "id": 2,
    "employee_id": "E1002",
    "name": "Jane Smith",
    "department": "Production B",
    "trainer": "Charlie",
    "trained_on_machines": "Packaging Line 1,Conveyor Belt Z",
    "last_trained_date": "2023-02-20",
    "next_due_date": "2024-02-20"
}

old_format_training_data_list_machines = {
    "id": 3,
    "employee_id": "E1003",
    "name": "Mike Brown",
    "department": "Maintenance",
    "trainer": "David",
    "trained_on_machines": ["Tool Grinder", "Hydraulic Press"],
    "last_trained_date": "2023-03-10",
    "next_due_date": "2024-03-10"
}

old_format_training_data_no_trainer = {
    "id": 4,
    "employee_id": "E1004",
    "name": "Sue Green",
    "department": "Lab",
    "trained_on_machines": ["Spectrometer"],
    "last_trained_date": "2023-04-05",
    "next_due_date": "2024-04-05"
}

empty_assignments_training_data = {
    "id": 5,
    "employee_id": "E1005",
    "name": "Chris White",
    "department": "Production A",
    "machine_trainer_assignments": [],
    "last_trained_date": "2023-05-01",
    "next_due_date": "2024-05-01"
}

# Import Training model
from app.models.training import Training

class TestTraining:
    def test_from_dict_new_format(self):
        training = Training.from_dict(new_format_training_data_valid)
        assert training.id == 1
        assert training.employee_id == "E1001"
        assert training.name == "John Doe"
        assert training.department == "Production A"
        assert len(training.machine_trainer_assignments) == 2
        assert training.machine_trainer_assignments[0] == {"machine": "CNC Mill", "trainer": "Alice"}
        assert training.machine_trainer_assignments[1] == {"machine": "Lathe X1000", "trainer": "Bob"}
        assert training.last_trained_date == "2023-01-15"
        assert training.next_due_date == "2024-01-15"

    def test_from_dict_old_format_str_machines(self):
        training = Training.from_dict(old_format_training_data_str_machines)
        assert training.id == 2
        assert training.employee_id == "E1002"
        assert training.name == "Jane Smith"
        assert training.department == "Production B"
        assert len(training.machine_trainer_assignments) == 2
        assert {"machine": "Packaging Line 1", "trainer": "Charlie"} in training.machine_trainer_assignments
        assert {"machine": "Conveyor Belt Z", "trainer": "Charlie"} in training.machine_trainer_assignments
        assert training.last_trained_date == "2023-02-20"

    def test_from_dict_old_format_list_machines(self):
        training = Training.from_dict(old_format_training_data_list_machines)
        assert training.id == 3
        assert training.department == "Maintenance"
        assert len(training.machine_trainer_assignments) == 2
        assert {"machine": "Tool Grinder", "trainer": "David"} in training.machine_trainer_assignments
        assert {"machine": "Hydraulic Press", "trainer": "David"} in training.machine_trainer_assignments

    def test_from_dict_old_format_no_trainer(self):
        training = Training.from_dict(old_format_training_data_no_trainer)
        assert training.id == 4
        assert training.department == "Lab"
        assert len(training.machine_trainer_assignments) == 1
        assert training.machine_trainer_assignments[0] == {"machine": "Spectrometer", "trainer": None}

    def test_from_dict_empty_assignments(self):
        training = Training.from_dict(empty_assignments_training_data)
        assert training.id == 5
        assert training.department == "Production A"
        assert training.machine_trainer_assignments == []

    def test_from_dict_none_assignments(self):
        data = new_format_training_data_valid.copy()
        data["machine_trainer_assignments"] = None
        training = Training.from_dict(data)
        assert training.machine_trainer_assignments == [] # Should default to empty list

    def test_from_dict_missing_assignments_and_old_fields(self):
        data = {
            "id": 6, "employee_id": "E1006", "name": "No Machines", "department": "QA",
            "last_trained_date": "2023-06-01"
        } # No machine_trainer_assignments, no trained_on_machines, no trainer
        training = Training.from_dict(data)
        assert training.machine_trainer_assignments == []

    def test_to_dict(self):
        training = Training.from_dict(new_format_training_data_valid)
        d = training.to_dict()
        assert d["id"] == 1
        assert d["employee_id"] == "E1001"
        assert d["name"] == "John Doe"
        assert d["department"] == "Production A"
        assert len(d["machine_trainer_assignments"]) == 2
        assert d["machine_trainer_assignments"][0] == {"machine": "CNC Mill", "trainer": "Alice"}
        assert d["machine_trainer_assignments"][1] == {"machine": "Lathe X1000", "trainer": "Bob"}
        assert d["last_trained_date"] == "2023-01-15"
        assert d["next_due_date"] == "2024-01-15"
        assert "trainer" not in d # Ensure old top-level trainer field is not present

    def test_to_dict_empty_assignments(self):
        training = Training.from_dict(empty_assignments_training_data)
        d = training.to_dict()
        assert d["machine_trainer_assignments"] == []
