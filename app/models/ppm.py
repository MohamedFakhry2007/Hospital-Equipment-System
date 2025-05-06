"""
Pydantic models for PPM (Planned Preventive Maintenance) data validation.
"""
from datetime import datetime
from typing import Dict, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class QuarterData(BaseModel):
    """Model for quarterly maintenance data."""
    date: str
    engineer: str
    
    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in DD/MM/YYYY format."""
        try:
            datetime.strptime(v, '%d/%m/%Y')
            return v
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Expected format: DD/MM/YYYY")

    @field_validator('engineer')
    @classmethod
    def validate_engineer(cls, v: str) -> str:
        """Validate engineer is not empty."""
        if not v.strip():
            raise ValueError("Engineer name cannot be empty")
        return v.strip()


class PPMEntry(BaseModel):
    """Model for PPM entries."""
    NO: Optional[int] = None
    EQUIPMENT: str
    MODEL: str
    MFG_SERIAL: str
    MANUFACTURER: str
    LOG_NO: str
    PPM: Literal['Yes', 'No']
    PPM_Q_I: QuarterData
    PPM_Q_II: QuarterData
    PPM_Q_III: QuarterData
    PPM_Q_IV: QuarterData    

    @field_validator('PPM')
    @classmethod
    def normalize_ppm(cls, v: str) -> str:
        """Normalize PPM value to Yes/No."""
        if v.strip().lower() == 'yes':
            return 'Yes'
        elif v.strip().lower() == 'no':
            return 'No'
        raise ValueError("PPM must be 'Yes' or 'No'")
    
    @field_validator('EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO')
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
    MFG_SERIAL: str
    MANUFACTURER: str
    LOG_NO: str
    PPM: Literal['Yes', 'No']
    OCM: Optional[str] = ''
    PPM_Q_I: Dict[str, str]
    PPM_Q_II: Dict[str, str]
    PPM_Q_III: Dict[str, str]
    PPM_Q_IV: Dict[str, str]