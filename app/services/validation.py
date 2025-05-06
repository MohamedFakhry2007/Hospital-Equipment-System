"""
Validation service for form and data validation.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional

from app.models.ppm import PPMEntry, QuarterData
from app.models.ocm import OCMEntry


logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating form data."""
    
    @staticmethod
    def validate_date_format(date_str: str) -> Tuple[bool, Optional[str]]:
        """Validate date is in DD/MM/YYYY format.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not date_str:
            return False, "Date cannot be empty"
            
        try:
            datetime.strptime(date_str, '%d/%m/%Y')
            return True, None
        except ValueError:
            return False, "Invalid date format. Expected format: DD/MM/YYYY"

    @staticmethod
    def validate_quarter_data(quarter_data: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate quarter data.
        
        Args:
            quarter_data: Dictionary containing date and engineer
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate date
        date_valid, date_error = ValidationService.validate_date_format(quarter_data.get('date', ''))
        if not date_valid:
            errors.append(date_error)
        
        # Validate engineer
        engineer = quarter_data.get('engineer', '')
        if not engineer.strip():
            errors.append("Engineer name cannot be empty")
        
        return len(errors) == 0, errors

    @staticmethod
    def validate_ppm_form(form_data: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        """Validate PPM form data.
        
        Args:
            form_data: Form data from request
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = {}
        
        # Required fields
        required_fields = ['EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO', 'PPM']
        for field in required_fields:
            if not form_data.get(field, '').strip():
                errors[field] = [f"{field} is required"]
        
        # Validate PPM value
        ppm_value = form_data.get('PPM', '').strip().lower()
        if ppm_value not in ('yes', 'no'):
            errors['PPM'] = ["PPM must be 'Yes' or 'No'"]
        
        # Validate quarter data
        for q in ['I', 'II', 'III', 'IV']:
            quarter_data = {
                'date': form_data.get(f'PPM_Q_{q}_date', ''),
                'engineer': form_data.get(f'PPM_Q_{q}_engineer', '')
            }
            
            q_valid, q_errors = ValidationService.validate_quarter_data(quarter_data)
            if not q_valid:
                errors[f'PPM_Q_{q}'] = q_errors
        
        return len(errors) == 0, errors

    @staticmethod
    def validate_ocm_form(form_data: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        """Validate OCM form data.
        
        Args:
            form_data: Form data from request
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = {}
        
        # Required fields
        required_fields = ['EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO', 'OCM', 'ENGINEER']
        for field in required_fields:
            if not form_data.get(field, '').strip():
                errors[field] = [f"{field} is required"]
        
        # Validate OCM value
        ocm_value = form_data.get('OCM', '').strip().lower()
        if ocm_value not in ('yes', 'no'):
            errors['OCM'] = ["OCM must be 'Yes' or 'No'"]
        
        return len(errors) == 0, errors

    @staticmethod
    def convert_ppm_form_to_model(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert form data to PPM model data.
        
        Args:
            form_data: Form data from request
            
        Returns:
            Converted model data
        """
        model_data = {
            'EQUIPMENT': form_data.get('EQUIPMENT', '').strip(),
            'MODEL': form_data.get('MODEL', '').strip(),
            'MFG_SERIAL': form_data.get('MFG_SERIAL', '').strip(),
            'MANUFACTURER': form_data.get('MANUFACTURER', '').strip(),
            'LOG_NO': form_data.get('LOG_NO', '').strip(),
            'PPM': form_data.get('PPM', '').strip().title()  # Normalize to 'Yes' or 'No'
        }
        
        # Convert quarter data
        for q in ['I', 'II', 'III', 'IV']:
            model_data[f'PPM_Q_{q}'] = {
                'date': form_data.get(f'PPM_Q_{q}_date', '').strip(),
                'engineer': form_data.get(f'PPM_Q_{q}_engineer', '').strip()
            }
        
        return model_data

    @staticmethod
    def convert_ocm_form_to_model(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert form data to OCM model data.
        
        Args:
            form_data: Form data from request
            
        Returns:
            Converted model data
        """
        model_data = {
            'EQUIPMENT': form_data.get('EQUIPMENT', '').strip(),
            'MODEL': form_data.get('MODEL', '').strip(),
            'MFG_SERIAL': form_data.get('MFG_SERIAL', '').strip(),
            'MANUFACTURER': form_data.get('MANUFACTURER', '').strip(),
            'LOG_NO': form_data.get('LOG_NO', '').strip(),
            'PPM': form_data.get('PPM', '').strip(),
            'OCM': form_data.get('OCM', '').strip().title(),  # Normalize to 'Yes' or 'No'
            'OCM_2024': form_data.get('OCM_2024', '').strip(),
            'ENGINEER': form_data.get('ENGINEER', '').strip(),
            'OCM_2025': form_data.get('OCM_2025', '').strip()
        }
        
        return model_data
