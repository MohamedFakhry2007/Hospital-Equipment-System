"""
Pydantic models for OCM (Other Corrective Maintenance) data validation.
"""
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


class OCMEntry(BaseModel):
    """Model for OCM entries."""
    NO: Optional[int] = None
    EQUIPMENT: str
    MODEL: str
    Name: Optional[str] = None
    MFG_SERIAL: str
    MANUFACTURER: str
    Department: str
    LOG_NO: str
    PPM: Optional[str] = ''
    Installation_Date: str
    Warranty_End: str
    Service_Date: str
    Next_Maintenance: str
    ENGINEER: str
    Status: Literal["Upcoming", "Overdue", "Maintained"]

    @field_validator('Installation_Date', 'Warranty_End', 'Service_Date', 'Next_Maintenance')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in DD/MM/YYYY format."""
        try:
            datetime.strptime(v, '%d/%m/%Y')
            return v
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Expected format: DD/MM/YYYY")

    @field_validator('EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO', 'ENGINEER', 'Department')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate required fields are not empty."""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class OCMEntryCreate(BaseModel):
    """Model for creating a new OCM entry (without NO field)."""
    EQUIPMENT: str
    MODEL: str
    Name: Optional[str] = None
    MFG_SERIAL: str
    MANUFACTURER: str
    Department: str
    LOG_NO: str
    PPM: Optional[str] = ''
    Installation_Date: str
    Warranty_End: str
    Service_Date: str
    Next_Maintenance: str
    ENGINEER: str
    Status: Literal["Upcoming", "Overdue", "Maintained"]
