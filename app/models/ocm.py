"""
Pydantic models for OCM (Other Corrective Maintenance) data validation.
"""
import logging
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class OCMEntry(BaseModel):
    """Model for OCM entries."""
    NO: int
    Department: str
    Name: str
    Model: str
    Serial: str
    Manufacturer: str
    Log_Number: str = Field(..., alias="Log_Number")
    Installation_Date: str = Field(..., alias="Installation_Date")
    Warranty_End: str = Field(..., alias="Warranty_End")
    Service_Date: str = Field(..., alias="Service_Date")
    Engineer: str
    Next_Maintenance: str = Field(..., alias="Next Maintenance")
    Status: Literal["Upcoming", "Scheduled", "Completed"]

    @field_validator('Installation_Date', 'Warranty_End', 'Service_Date', 'Next_Maintenance')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in MM/DD/YYYY format."""
        logger.debug(f"Validating date format for value: {v}")
        try:
            datetime.strptime(v, '%m/%d/%Y')
            return v
        except ValueError as e:
            logger.error(f"Date validation failed for value '{v}': {str(e)}")
            raise ValueError(f"Invalid date format: {v}. Expected format: MM/DD/YYYY")

    @field_validator('Department', 'Name', 'Model', 'Serial', 'Manufacturer', 'Log_Number', 'Engineer')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate required fields are not empty."""
        logger.debug(f"Validating non-empty field value: {v}")
        if not v.strip():
            logger.error(f"Empty field validation failed")
            raise ValueError("Field cannot be empty")
        return v.strip()

    class Config:
        """Pydantic model configuration."""
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.strftime('%m/%d/%Y')
        }


class OCMEntryCreate(BaseModel):
    """Model for creating a new OCM entry (without NO field)."""
    EQUIPMENT: str
    MODEL: str
    Name: Optional[str] = None
    SERIAL: str
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
