"""
Pydantic models for PPM (Planned Preventive Maintenance) data validation.
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

class QuarterData(BaseModel):
    """Model for quarterly maintenance data."""
    engineer: Optional[str] = None
    quarter_date: Optional[str] = None
    status: Optional[Literal["Upcoming", "Overdue", "Maintained"]] = None

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
    Department: str
    Name: Optional[str] = None
    MODEL: str
    SERIAL: str
    MANUFACTURER: str
    LOG_Number: str
    Installation_Date: Optional[str] = None
    Warranty_End: Optional[str] = None
    PPM_Q_I: QuarterData
    PPM_Q_II: QuarterData
    PPM_Q_III: QuarterData
    PPM_Q_IV: QuarterData
    Status: Optional[Literal["Upcoming", "Overdue", "Maintained"]] = None

    @field_validator('Installation_Date', 'Warranty_End')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date is in DD/MM/YYYY format (preferred) or YYYY-MM-DD format (backward compatibility) if provided."""
        if v is None or not v.strip() or v.strip().upper() == 'N/A':
            return None  # Allow None, empty string, or N/A values
        try:
            # Try DD/MM/YYYY format first (preferred)
            datetime.strptime(v, '%d/%m/%Y')
            return v
        except ValueError:
            try:
                # Fallback to HTML5 date format (YYYY-MM-DD) for backward compatibility
                parsed_date = datetime.strptime(v, '%Y-%m-%d')
                # Convert to DD/MM/YYYY format for consistency
                return parsed_date.strftime('%d/%m/%Y')
            except ValueError:
                raise ValueError(f"Invalid date format: {v}. Expected format: DD/MM/YYYY or N/A")

    @field_validator('MODEL', 'SERIAL', 'MANUFACTURER', 'LOG_Number', 'Department')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate required fields are not empty."""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_model(self) -> 'PPMEntry':
        """Validate the complete model."""
        # Ensure SERIAL is unique (this will be checked at the service level)
        return self

class PPMImportEntry(BaseModel):
    Department: str
    Name: str
    MODEL: str
    SERIAL: str
    MANUFACTURER: str
    LOG_Number: str
    PPM_Q_I_date: str

    Installation_Date: Optional[str] = None
    Warranty_End: Optional[str] = None
    PPM_Q_I_engineer: Optional[str] = None
    PPM_Q_II_engineer: Optional[str] = None
    PPM_Q_III_engineer: Optional[str] = None
    PPM_Q_IV_engineer: Optional[str] = None

    @field_validator('Installation_Date', 'Warranty_End')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date is in DD/MM/YYYY format (preferred) or YYYY-MM-DD format (backward compatibility) if provided."""
        logger.debug(f"PPMImportEntry validation called with value: '{v}' (type: {type(v)})")
        if v is None or not v.strip() or v.strip().upper() == 'N/A':
            logger.debug(f"PPMImportEntry: Converting '{v}' to None")
            return None  # Allow None, empty string, or N/A values
        try:
            # Try DD/MM/YYYY format first (preferred)
            datetime.strptime(v, '%d/%m/%Y')
            return v
        except ValueError:
            try:
                # Fallback to HTML5 date format (YYYY-MM-DD) for backward compatibility
                parsed_date = datetime.strptime(v, '%Y-%m-%d')
                # Convert to DD/MM/YYYY format for consistency
                return parsed_date.strftime('%d/%m/%Y')
            except ValueError:
                logger.error(f"PPMImportEntry date validation failed for: '{v}'")
                raise ValueError(f"Invalid date format: {v}. Expected format: DD/MM/YYYY or N/A")

    @field_validator('MODEL', 'SERIAL', 'MANUFACTURER', 'LOG_Number', 'Department', 'PPM_Q_I_date')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

class PPMEntryCreate(BaseModel):
    """Model for creating a new PPM entry (without NO field)."""
    NO: Optional[int] = None
    Department: str
    Name: Optional[str] = None
    MODEL: str
    SERIAL: str
    MANUFACTURER: str
    LOG_Number: str
    Installation_Date: Optional[str] = None
    Warranty_End: Optional[str] = None
    PPM_Q_I: QuarterData
    PPM_Q_II: QuarterData
    PPM_Q_III: QuarterData
    PPM_Q_IV: QuarterData
    Status: Optional[Literal["Upcoming", "Overdue", "Maintained"]] = None