import pytest
from pydantic import ValidationError

from app.models.ppm import PPMEntry, QuarterData
from app.models.ocm import OCMEntry


# Test data for PPMEntry
valid_ppm_data = {
    "EQUIPMENT": "Test Equipment",
    "MODEL": "Test Model",
    "Name": "Optional Name",
    "MFG_SERIAL": "SN123",
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
    "MFG_SERIAL": "SN456",
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
        required_fields = ["EQUIPMENT", "MODEL", "MFG_SERIAL", "MANUFACTURER", "Department", "LOG_NO"]
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
        required_fields = ["EQUIPMENT", "MODEL", "MFG_SERIAL", "MANUFACTURER", "Department", "LOG_NO", "ENGINEER"]
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
