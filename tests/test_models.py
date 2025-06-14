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
    "Eng1": "Engineer A",
    "Eng2": "Engineer B",
    "Eng3": "Engineer C",
    "Eng4": "Engineer D",
    "Status": "Upcoming",
    "PPM_Q_I": {"engineer": "Eng Q1"},
    "PPM_Q_II": {"engineer": "Eng Q2"},
    "PPM_Q_III": {"engineer": "Eng Q3"},
    "PPM_Q_IV": {"engineer": "Eng Q4"},
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

    def test_invalid_date_format(self):
        data = valid_ppm_data.copy()
        data["Installation_Date"] = "2023-01-01" # Invalid format
        with pytest.raises(ValidationError):
            PPMEntry(**data)

        data = valid_ppm_data.copy()
        data["Warranty_End"] = "01-01-2025" # Invalid format
        with pytest.raises(ValidationError):
            PPMEntry(**data)

    def test_empty_required_fields(self):
        required_fields = ["EQUIPMENT", "MODEL", "MFG_SERIAL", "MANUFACTURER", "Department", "LOG_NO", "Eng1", "Eng2", "Eng3", "Eng4"]
        for field in required_fields:
            data = valid_ppm_data.copy()
            data[field] = ""
            with pytest.raises(ValidationError):
                PPMEntry(**data)

    def test_invalid_status(self):
        data = valid_ppm_data.copy()
        data["Status"] = "InvalidStatus"
        with pytest.raises(ValidationError):
            PPMEntry(**data)

    def test_quarter_data_empty_engineer(self):
        data = valid_ppm_data.copy()
        data["PPM_Q_I"] = {"engineer": " "}
        with pytest.raises(ValidationError):
            PPMEntry(**data)


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
