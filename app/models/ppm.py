"""
Pydantic models for PPM (Planned Preventive Maintenance) data validation.
"""
from datetime import datetime
from typing import Dict, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class QuarterData(BaseModel):
    """Model for quarterly maintenance data."""
    engineer: Optional[str] = None
    quarter_date: Optional[str] = None

    @field_validator('engineer')
    @classmethod
    def validate_engineer(cls, v: Optional[str]) -> Optional[str]:
        """Validate engineer is not empty if provided."""
        if v is None or not v.strip():
            return None  # Allow None or empty string
        return v.strip()


class PPMEntry(BaseModel):
    """Model for PPM entries."""
    NO: Optional[int] = None
    EQUIPMENT: str
    MODEL: str
    Name: Optional[str] = None
    MFG_SERIAL: str
    MANUFACTURER: str
    Department: str
    LOG_NO: str
    Installation_Date: Optional[str] = None
    Warranty_End: Optional[str] = None
    Status: Literal["Upcoming", "Overdue", "Maintained"]
    PPM_Q_I: QuarterData
    PPM_Q_II: QuarterData
    PPM_Q_III: QuarterData
    PPM_Q_IV: QuarterData

    @field_validator('Installation_Date', 'Warranty_End')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date is in DD/MM/YYYY format if provided."""
        if v is None or not v.strip():
            return v  # Allow None or empty string
        try:
            datetime.strptime(v, '%d/%m/%Y')
            return v
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Expected format: DD/MM/YYYY")

    @field_validator('EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO', 'Department')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate required fields are not empty."""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_model(self) -> 'PPMEntry':
        """Validate the complete model."""
        # Ensure MFG_SERIAL is unique (this will be checked at the service level)
        return self


class PPMEntryCreate(BaseModel):
    """Model for creating a new PPM entry (without NO field)."""
    EQUIPMENT: str
    MODEL: str
    Name: Optional[str] = None
    MFG_SERIAL: str
    MANUFACTURER: str
    Department: str
    LOG_NO: str
    Installation_Date: Optional[str] = None
    Warranty_End: Optional[str] = None
    Status: Literal["Upcoming", "Overdue", "Maintained"]
    OCM: Optional[str] = ''
    PPM_Q_I: Dict[str, str]
    PPM_Q_II: Dict[str, str]
    PPM_Q_III: Dict[str, str]
    PPM_Q_IV: Dict[str, str]