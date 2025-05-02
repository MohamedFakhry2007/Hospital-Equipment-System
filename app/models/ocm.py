"""
Pydantic models for OCM (Other Corrective Maintenance) data validation.
"""
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


class OCMEntry(BaseModel):
    """Model for OCM entries."""
    NO: Optional[int] = None
    EQUIPMENT: str
    MODEL: str
    MFG_SERIAL: str
    MANUFACTURER: str
    LOG_NO: str
    PPM: Optional[str] = ''
    OCM: Literal['Yes', 'No']
    OCM_2024: str
    ENGINEER: str
    OCM_2025: str

    @field_validator('OCM')
    @classmethod
    def normalize_ocm(cls, v: str) -> str:
        """Normalize OCM value to Yes/No."""
        if v.strip().lower() == 'yes':
            return 'Yes'
        elif v.strip().lower() == 'no':
            return 'No'
        raise ValueError("OCM must be 'Yes' or 'No'")
    
    @field_validator('EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO', 'ENGINEER')
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
    MFG_SERIAL: str
    MANUFACTURER: str
    LOG_NO: str
    PPM: Optional[str] = ''
    OCM: Literal['Yes', 'No']
    OCM_2024: str
    ENGINEER: str
    OCM_2025: str
