"""
Validation service for form and data validation.
"""
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Dict, Any, Tuple, List, Optional

from app.models.ppm import PPMEntry, QuarterData
from app.models.ocm import OCMEntry


logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating form data."""
    
    logger.debug("Initializing ValidationService")
    
    @staticmethod
    def validate_date_format(date_str: str) -> Tuple[bool, Optional[str]]:
        """Validate date is in DD/MM/YYYY format (preferred) or YYYY-MM-DD format (backward compatibility).
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating date: '{date_str}'")
        if not date_str:
            return False, "Date cannot be empty"
            
        try:
            # Try parsing as DD/MM/YYYY first (preferred format)
            parsed_date = datetime.strptime(date_str, '%d/%m/%Y')
            return True, None
        except ValueError:
            try:
                # Try parsing as YYYY-MM-DD for backward compatibility
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                return True, None
            except ValueError:
                return False, "Invalid date format. Expected format: DD/MM/YYYY"

    @staticmethod
    def convert_date_to_ddmmyyyy(date_str: str) -> str:
        """Convert date string to DD/MM/YYYY format.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Date string in DD/MM/YYYY format
        """
        if not date_str or date_str.strip() == '':
            return date_str
            
        try:
            # Try DD/MM/YYYY first (already in correct format)
            parsed_date = datetime.strptime(date_str, '%d/%m/%Y')
            return date_str  # Already in correct format
        except ValueError:
            try:
                # Try YYYY-MM-DD and convert
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                return parsed_date.strftime('%d/%m/%Y')
            except ValueError:
                # Return original if parsing fails
                return date_str

    @staticmethod
    def validate_ppm_form(form_data: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        errors = {}
        required_fields = ['EQUIPMENT', 'MODEL', 'SERIAL', 'MANUFACTURER', 'LOG_NO', 'PPM']
        for field in required_fields:
            if not form_data.get(field, '').strip():
                errors[field] = [f"{field} is required"]
        
        # Validate PPM value
        ppm_value = form_data.get('PPM', '').strip().lower()
        if ppm_value not in ('yes', 'no'):
            errors['PPM'] = ["PPM must be 'Yes' or 'No'"]
        
        q1_date = form_data.get('PPM_Q_I_date', '').strip()
        date_valid, date_error = ValidationService.validate_date_format(q1_date)
        if not date_valid:
            errors['PPM_Q_I_date'] = [date_error]

        for q in ['I', 'II', 'III', 'IV']:
            if not form_data.get(f'PPM_Q_{q}_engineer', '').strip():
                errors[f'PPM_Q_{q}_engineer'] = ["Engineer name cannot be empty"]
        return len(errors) == 0, errors

    @staticmethod
    def validate_ocm_form(form_data: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        """Validate OCM form data."""
        errors = {}
        
        # Required fields
        required_fields = ['EQUIPMENT', 'MODEL', 'SERIAL', 'MANUFACTURER', 'LOG_NO', 'OCM', 'ENGINEER']
        for field in required_fields:
            if not form_data.get(field, '').strip():
                errors[field] = [f"{field} is required"]
        
        # Validate OCM value
        ocm_value = form_data.get('OCM', '').strip().lower()
        if ocm_value not in ('yes', 'no'):
            errors['OCM'] = ["OCM must be 'Yes' or 'No'"]
        
        # Validate date fields
        date_fields = ['Installation_Date', 'Warranty_End', 'Service_Date', 'Next_Maintenance']
        for field in date_fields:
            date_str = form_data.get(field, '').strip()
            if date_str:  # Only validate if date is provided
                date_valid, date_error = ValidationService.validate_date_format(date_str)
                if not date_valid:
                    errors[field] = [date_error]
        
        return len(errors) == 0, errors

    @staticmethod
    def validate_quarterly_assignment(quarter_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate quarterly assignment data for PPM.
        
        Args:
            quarter_data: Dictionary containing engineer and quarter_date fields
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        engineer = quarter_data.get('engineer', '').strip()
        quarter_date = quarter_data.get('quarter_date', '').strip()
        
        if not quarter_date:
            return False, "Quarter date is required"
            
        # Validate date format
        try:
            # First try DD/MM/YYYY format
            datetime.strptime(quarter_date, '%d/%m/%Y')
            return True, ""
        except ValueError:
            try:
                # Fallback to YYYY-MM-DD format for backward compatibility
                datetime.strptime(quarter_date, '%Y-%m-%d')
                return True, ""
            except ValueError:
                return False, "Invalid date format. Expected format: DD/MM/YYYY"

    @staticmethod
    def calculate_quarter_dates_from_q1(q1_date_str: str) -> List[str]:
        """Calculate all quarter dates from Q1 date.
        
        Args:
            q1_date_str: Q1 date in DD/MM/YYYY format
            
        Returns:
            List of quarter dates in DD/MM/YYYY format
        """
        try:
            # Parse Q1 date
            q1_date = datetime.strptime(q1_date_str, '%d/%m/%Y')
            
            # Calculate subsequent quarters (3 months apart)
            quarter_dates = [q1_date_str]  # Q1 date
            current_date = q1_date
            
            for i in range(3):  # Q2, Q3, Q4
                current_date = current_date + relativedelta(months=3)
                quarter_dates.append(current_date.strftime('%d/%m/%Y'))
            
            return quarter_dates
            
        except ValueError:
            # If parsing fails, try YYYY-MM-DD format for backward compatibility
            try:
                q1_date = datetime.strptime(q1_date_str, '%Y-%m-%d')
                q1_date_formatted = q1_date.strftime('%d/%m/%Y')  # Standardize to DD/MM/YYYY
                
                quarter_dates = [q1_date_formatted]  # Q1 date
                current_date = q1_date
                
                for i in range(3):  # Q2, Q3, Q4
                    current_date = current_date + relativedelta(months=3)
                    quarter_dates.append(current_date.strftime('%d/%m/%Y'))
                
                return quarter_dates
                
            except ValueError:
                raise ValueError("Invalid Quarter I date format. Please use DD/MM/YYYY")

    @staticmethod
    def normalize_all_dates_in_entry(entry: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Normalize all date fields in an entry to DD/MM/YYYY format.
        
        Args:
            entry: Equipment entry dictionary
            data_type: 'ppm' or 'ocm'
            
        Returns:
            Entry with all dates normalized to DD/MM/YYYY format
        """
        normalized_entry = entry.copy()
        
        if data_type == 'ppm':
            # Normalize main dates
            for field in ['Installation_Date', 'Warranty_End']:
                if field in normalized_entry and normalized_entry[field]:
                    normalized_entry[field] = ValidationService.convert_date_to_ddmmyyyy(normalized_entry[field])
            
            # Normalize quarter dates
            for quarter in ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']:
                if quarter in normalized_entry and normalized_entry[quarter].get('quarter_date'):
                    normalized_entry[quarter]['quarter_date'] = ValidationService.convert_date_to_ddmmyyyy(
                        normalized_entry[quarter]['quarter_date']
                    )
                    
        elif data_type == 'ocm':
            # Normalize OCM date fields
            for field in ['Installation_Date', 'Warranty_End', 'Service_Date', 'Next_Maintenance']:
                if field in normalized_entry and normalized_entry[field]:
                    normalized_entry[field] = ValidationService.convert_date_to_ddmmyyyy(normalized_entry[field])
        
        return normalized_entry
