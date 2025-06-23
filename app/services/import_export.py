"""
Service for importing and exporting data.
"""
import logging
import os
from io import StringIO
from typing import List, Dict, Any, Literal, Tuple
import json
from datetime import datetime, timedelta

import pandas as pd
from pydantic import ValidationError

from app.models.ppm import PPMImportEntry, PPMEntry
from app.models.ocm import OCMEntry
from app.models.training import Training
from app.services.data_service import DataService


logger = logging.getLogger('app')
logger.debug("Initializing import/export service")

class ImportExportService:
    """Service for handling import and export operations."""
    
    @staticmethod
    def detect_csv_type(columns: List[str]) -> Literal['ppm', 'ocm', 'training', 'unknown']:
        """Detect the type of CSV file based on its columns."""
        # Print raw columns first
        print(f"Raw columns: {columns}")
        
        # Strip whitespace and convert to set for comparison
        columns_set = {col.strip() for col in columns}
        print(f"Processed columns: {sorted(columns_set)}")
        
        ppm_required = {
            'Department',
            'Name',
            'MODEL',
            'SERIAL',
            'MANUFACTURER',
            'LOG_Number',
            'PPM_Q_I_date'
        }
        
        # OCM can have columns with spaces or underscores
        ocm_required_with_spaces = {
            'Department',
            'Name',
            'Model',
            'Serial',
            'Manufacturer',
            'Log Number',
            'Installation Date',
            'Service Date',
            'Engineer'
        }
        
        ocm_required_with_underscores = {
            'Department',
            'Name',
            'Model',
            'Serial',
            'Manufacturer',
            'Log_Number',
            'Installation_Date',
            'Service_Date',
            'Engineer'
        }
        
        training_required = {
            'id',
            'employee_id',
            'name',
            'department',
            'machine_trainer_assignments'
        }
        
        print(f"OCM required columns (spaces): {sorted(ocm_required_with_spaces)}")
        print(f"OCM required columns (underscores): {sorted(ocm_required_with_underscores)}")
        
        # Check both OCM formats
        ocm_spaces_match = ocm_required_with_spaces.issubset(columns_set)
        ocm_underscores_match = ocm_required_with_underscores.issubset(columns_set)
        
        if not ocm_spaces_match and not ocm_underscores_match:
            missing_spaces = ocm_required_with_spaces - columns_set
            missing_underscores = ocm_required_with_underscores - columns_set
            print(f"Missing OCM columns (spaces format): {sorted(missing_spaces)}")
            print(f"Missing OCM columns (underscores format): {sorted(missing_underscores)}")
        
        if ppm_required.issubset(columns_set):
            return 'ppm'
        elif ocm_spaces_match or ocm_underscores_match:
            return 'ocm'
        elif training_required.issubset(columns_set):
            return 'training'
        return 'unknown'

    @staticmethod
    def export_to_csv(data_type: Literal['ppm', 'ocm', 'training'], output_path: str = None) -> Tuple[bool, str, str]:
        """Export data to CSV file.
        
        Args:
            data_type: Type of data to export ('ppm', 'ocm', or 'training')
            output_path: Path to save the CSV file (optional)
            
        Returns:
            Tuple of (success, message, csv_content)
        """
        try:
            logger.debug(f"Starting {data_type} data export in ImportExportService")
            # Load data
            data = DataService.load_data(data_type)
            
            if not data:
                logger.warning(f"No {data_type.upper()} data found for export")
                return False, f"No {data_type.upper()} data to export", ""
            
            logger.debug(f"Found {len(data)} {data_type} entries to export")
            flat_data = []
            
            # Log structure of first entry for debugging
            if data:
                logger.debug(f"First entry structure: {json.dumps(data[0], indent=2)}")
            
            for idx, entry in enumerate(data):
                logger.debug(f"Processing entry {idx + 1}/{len(data)} with ID: {entry.get('SERIAL') if data_type == 'ppm' else (entry.get('Serial') if data_type == 'ocm' else entry.get('id'))}")
                
                if data_type == 'ppm':
                    # PPM export handling with all fields and N/A handling
                    flat_entry = {
                        'NO': entry.get('NO') or 'N/A',
                        'Department': entry.get('Department') or 'N/A',
                        'Name': entry.get('Name') or 'N/A',
                        'MODEL': entry.get('MODEL') or 'N/A',
                        'SERIAL': entry.get('SERIAL') or 'N/A',
                        'MANUFACTURER': entry.get('MANUFACTURER') or 'N/A',
                        'LOG_Number': entry.get('LOG_Number') or 'N/A',
                        'Installation_Date': entry.get('Installation_Date') or 'N/A',
                        'Warranty_End': entry.get('Warranty_End') or 'N/A'
                    }
                    
                    quarter_map = [
                        ('I', 'PPM_Q_I'),
                        ('II', 'PPM_Q_II'),
                        ('III', 'PPM_Q_III'),
                        ('IV', 'PPM_Q_IV')
                    ]
                    
                    # Calculate quarter statuses dynamically like the table view
                    today = datetime.now().date()
                    
                    for roman, q_key in quarter_map:
                        q_data = entry.get(q_key, {})
                        quarter_date_str = q_data.get('quarter_date')
                        engineer = q_data.get('engineer')
                        engineer = engineer.strip() if engineer else ''
                        
                        flat_entry[f'PPM_Q_{roman}_date'] = quarter_date_str or 'N/A'
                        flat_entry[f'PPM_Q_{roman}_engineer'] = engineer or 'N/A'
                        
                        # Calculate status dynamically based on date and engineer
                        if quarter_date_str:
                            try:
                                # Use the same flexible date parsing as the table view
                                from app.services.email_service import EmailService
                                quarter_date = EmailService.parse_date_flexible(quarter_date_str).date()
                                
                                # Calculate status based on date and engineer (same logic as table view)
                                if quarter_date < today:
                                    if engineer and engineer.strip():  # Check for non-empty engineer
                                        quarter_status = 'Maintained'
                                    else:
                                        quarter_status = 'Overdue'
                                elif quarter_date == today:
                                    quarter_status = 'Maintained'
                                else:
                                    quarter_status = 'Upcoming'
                                
                                flat_entry[f'PPM_Q_{roman}_status'] = quarter_status
                                
                            except (ValueError, ImportError):
                                # Invalid date format or import error, set default
                                flat_entry[f'PPM_Q_{roman}_status'] = 'N/A'
                        else:
                            # No date specified
                            flat_entry[f'PPM_Q_{roman}_status'] = 'N/A'
                    
                    # Overall status column removed - only individual quarter statuses are exported
                    
                elif data_type == 'ocm':  # OCM export handling with N/A handling
                    flat_entry = {
                        'NO': entry.get('NO') or 'N/A',
                        'Department': entry.get('Department') or 'N/A',
                        'Name': entry.get('Name') or 'N/A',
                        'Model': entry.get('Model') or 'N/A',
                        'Serial': entry.get('Serial') or 'N/A',
                        'Manufacturer': entry.get('Manufacturer') or 'N/A',
                        'Log_Number': entry.get('Log_Number') or 'N/A',
                        'Installation_Date': entry.get('Installation_Date') or 'N/A',
                        'Warranty_End': entry.get('Warranty_End') or 'N/A',
                        'Service_Date': entry.get('Service_Date') or 'N/A',
                        'Engineer': entry.get('Engineer') or 'N/A',
                        'Next_Maintenance': entry.get('Next_Maintenance') or 'N/A',
                        'Status': entry.get('Status') or 'N/A'
                    }
                    
                else:  # Training export handling
                    flat_entry = {
                        'id': entry.get('id') or 'N/A',
                        'employee_id': entry.get('employee_id') or 'N/A',
                        'name': entry.get('name') or 'N/A',
                        'department': entry.get('department') or 'N/A',
                        'machine_trainer_assignments': json.dumps(entry.get('machine_trainer_assignments', [])) if entry.get('machine_trainer_assignments') else 'N/A',
                        'last_trained_date': entry.get('last_trained_date') or 'N/A',
                        'next_due_date': entry.get('next_due_date') or 'N/A'
                    }
                
                flat_data.append(flat_entry)
            
            df = pd.DataFrame(flat_data)
            
            # Ensure appropriate first column based on data type
            if data_type in ['ppm', 'ocm'] and 'NO' in df.columns:
                cols = ['NO'] + [col for col in df.columns if col != 'NO']
                df = df[cols]
            elif data_type == 'training' and 'id' in df.columns:
                cols = ['id'] + [col for col in df.columns if col != 'id']
                df = df[cols]
            
            # Replace any remaining empty strings or None values with N/A
            df = df.fillna('N/A')
            df = df.replace('', 'N/A')
            
            csv_content = df.to_csv(index=False)
            
            if output_path:
                df.to_csv(output_path, index=False)
                logger.info(f"Successfully exported {data_type} data to {output_path}")
            
            return True, f"Successfully processed {len(flat_data)} entries", csv_content
            
        except Exception as e:
            error_msg = f"Error exporting {data_type} data: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, ""

    @staticmethod
    def import_from_csv(data_type: Literal['ppm', 'ocm', 'training'], file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Import data from CSV file.
        
        Args:
            data_type: Type of data to import ('ppm', 'ocm', or 'training')
            file_path: Path to CSV file
            
        Returns:
            Tuple of (success, message, import_stats)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}", {}

            # Read CSV with dtype=str to prevent automatic type conversion that adds .0 to employee IDs
            df = pd.read_csv(file_path, dtype=str)
            # Handle N/A values properly - replace NaN with empty string, but keep 'N/A' strings as 'N/A'
            df = df.fillna('')
            # Convert empty strings back to N/A for consistency
            df = df.replace('', 'N/A')

            # Auto-detect type if needed
            detected_type = ImportExportService.detect_csv_type(df.columns.tolist())
            if detected_type == 'unknown':
                return False, "Invalid CSV format - required columns missing", {}
            elif data_type != detected_type:
                return False, f"CSV format mismatch - file appears to be {detected_type} format, but {data_type} was requested", {}

            # Map CSV columns to model field names for OCM
            if data_type == 'ocm':
                column_mapping = {
                    'Log Number': 'Log_Number',
                    'Installation Date': 'Installation_Date',
                    'Service Date': 'Service_Date',
                    'Warranty End': 'Warranty_End'
                    # Note: Next_Maintenance and Status are auto-generated, not from CSV
                }
                # Rename columns to match model field names
                df = df.rename(columns=column_mapping)
                logger.debug(f"Renamed columns: {df.columns.tolist()}")

            current_data = DataService.load_data(data_type)
            
            # Determine key field based on data type
            if data_type == 'ppm':
                key_field = 'SERIAL'
            elif data_type == 'ocm':
                key_field = 'Serial'
            else:  # training
                key_field = 'id'
                
            existing_keys = {entry.get(key_field) for entry in current_data}
            
            # Process rows
            new_entries = []
            skipped_entries = []
            error_entries = []
            
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                logger.debug(f"Processing row {idx + 1}: {row_dict}")
                
                try:
                    # Remove NO field if present for equipment data, it will be reassigned
                    if data_type in ['ppm', 'ocm']:
                        row_dict.pop('NO', None)
                    
                    # Check for duplicate key
                    if row_dict[key_field] in existing_keys:
                        logger.warning(f"Skipping row {idx + 1}: Duplicate {key_field} {row_dict[key_field]}")
                        skipped_entries.append(f"Row {idx + 1}: Duplicate {key_field} {row_dict[key_field]}")
                        continue
                    
                    if data_type == 'ppm':
                        # First validate the import format
                        import_entry = PPMImportEntry(**row_dict)
                        # Then transform to the proper nested structure
                        transformed_dict = ImportExportService.transform_ppm_entry(row_dict)
                        entry = PPMEntry(**transformed_dict)
                    elif data_type == 'ocm':
                        # Add NO field for OCM entries
                        row_dict['NO'] = idx + 1
                        
                        # Enhanced data cleaning and validation
                        row_dict = ImportExportService._clean_ocm_data(row_dict)
                        
                        # Handle OCM data
                        entry = OCMEntry(**row_dict)
                    else:  # training
                        # Parse machine_trainer_assignments JSON if it's a string
                        if isinstance(row_dict.get('machine_trainer_assignments'), str):
                            try:
                                row_dict['machine_trainer_assignments'] = json.loads(row_dict['machine_trainer_assignments'])
                            except json.JSONDecodeError:
                                # If JSON parsing fails, set to empty list
                                row_dict['machine_trainer_assignments'] = []
                        
                        # Handle training data
                        entry = Training.from_dict(row_dict)
                    
                    if data_type == 'training':
                        validated_entry = entry.to_dict()
                    else:
                        validated_entry = entry.model_dump()
                        
                    logger.debug(f"Successfully validated row {idx + 1}")
                    new_entries.append(validated_entry)
                    existing_keys.add(row_dict[key_field])
                    
                except ValidationError as ve:
                    logger.error(f"Validation error in row {idx + 1}: {str(ve)}")
                    error_entries.append(f"Row {idx + 1}: Validation error - {str(ve)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing row {idx + 1}: {str(e)}")
                    error_entries.append(f"Row {idx + 1}: {str(e)}")
                    continue
            
            if new_entries:
                # Add entries and reindex (for equipment data)
                current_data.extend(new_entries)
                if data_type in ['ppm', 'ocm']:
                    current_data = DataService._reindex_entries(current_data)
                DataService.save_data(current_data, data_type)
                logger.info(f"Successfully imported {len(new_entries)} entries")
            
            stats = {
                "total_rows": len(df),
                "imported": len(new_entries),
                "skipped": len(skipped_entries),
                "errors": len(error_entries),
                "skipped_details": skipped_entries,
                "error_details": error_entries
            }
            
            logger.info(f"Import statistics: {stats}")
            message = f"Import complete. {len(new_entries)} entries imported, {len(skipped_entries)} skipped, {len(error_entries)} errors."
            return True, message, stats
            
        except Exception as e:
            error_msg = f"Error importing {data_type} data: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {
                "total_rows": 0,
                "imported": 0,
                "skipped": 0,
                "errors": 1,
                "error_details": [str(e)]
            }
    
    @staticmethod
    def _clean_ocm_data(row_dict: dict) -> dict:
        """Clean and validate OCM data with enhanced error handling."""
        import re
        from datetime import datetime
        
        def clean_date_value(date_str: str) -> str:
            """Clean and validate date values, converting to DD/MM/YYYY format."""
            if not date_str or str(date_str).strip().upper() in ['N/A', 'NULL', 'NONE', '', 'NAN']:
                return 'N/A'
            
            date_str = str(date_str).strip()
            
            # Try different date formats
            date_formats = [
                '%d/%m/%Y',    # DD/MM/YYYY (preferred)
                '%m/%d/%Y',    # MM/DD/YYYY (US format)
                '%Y-%m-%d',    # YYYY-MM-DD (ISO format)
                '%d-%m-%Y',    # DD-MM-YYYY
                '%m-%d-%Y',    # MM-DD-YYYY
                '%d.%m.%Y',    # DD.MM.YYYY
                '%m.%d.%Y',    # MM.DD.YYYY
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%d/%m/%Y')
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse date '{date_str}', using default")
            return '01/01/2024'  # Default date
        
        def clean_text_value(text_str: str, field_name: str = '') -> str:
            """Clean text values, providing defaults for required fields."""
            if not text_str or str(text_str).strip().upper() in ['N/A', 'NULL', 'NONE', 'NAN', '']:
                # Provide meaningful defaults for required fields
                defaults = {
                    'Department': 'UNKNOWN_DEPT',
                    'Name': 'UNKNOWN_EQUIPMENT',
                    'Model': 'UNKNOWN_MODEL',
                    'Serial': f'UNKNOWN_SERIAL_{row_dict.get("NO", "X")}',
                    'Manufacturer': 'UNKNOWN_MFG',
                    'Log_Number': f'LOG_{row_dict.get("NO", "X")}',
                    'Engineer': 'UNKNOWN_ENGINEER'
                }
                return defaults.get(field_name, 'UNKNOWN')
            
            # Clean up the text
            cleaned = str(text_str).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Remove extra whitespace
            return cleaned if cleaned else 'UNKNOWN'
        
        # Create a copy to avoid modifying original
        cleaned_data = row_dict.copy()
        
        # Clean required text fields
        text_fields = ['Department', 'Name', 'Model', 'Serial', 'Manufacturer', 'Log_Number', 'Engineer']
        for field in text_fields:
            if field in cleaned_data:
                cleaned_data[field] = clean_text_value(cleaned_data[field], field)
        
        # Clean date fields
        date_fields = ['Installation_Date', 'Warranty_End', 'Service_Date']
        for field in date_fields:
            if field in cleaned_data:
                cleaned_data[field] = clean_date_value(cleaned_data[field])
        
        # Auto-generate Next_Maintenance and Status based on Service_Date
        service_date_str = cleaned_data.get('Service_Date', '').strip()
        if service_date_str and service_date_str != 'N/A':
            try:
                service_date = datetime.strptime(service_date_str, '%d/%m/%Y')
                
                # Generate next maintenance date (one year later)
                next_maintenance_date = service_date.replace(year=service_date.year + 1)
                cleaned_data['Next_Maintenance'] = next_maintenance_date.strftime('%d/%m/%Y')
                
                # Determine status based on current date vs next maintenance date
                current_date = datetime.now()
                if next_maintenance_date < current_date:
                    cleaned_data['Status'] = 'Overdue'
                else:
                    cleaned_data['Status'] = 'Upcoming'
                    
                logger.debug(f"Auto-generated: Next_Maintenance={cleaned_data['Next_Maintenance']}, Status={cleaned_data['Status']}")
                
            except ValueError:
                # Fallback values
                cleaned_data['Next_Maintenance'] = '01/01/2025'
                cleaned_data['Status'] = 'Upcoming'
                logger.warning(f"Could not parse Service_Date '{service_date_str}', using defaults")
        else:
            # Default values for missing service date
            cleaned_data['Next_Maintenance'] = '01/01/2025'
            cleaned_data['Status'] = 'Upcoming'
        
        # Ensure NO field is a proper integer
        if 'NO' in cleaned_data:
            try:
                cleaned_data['NO'] = int(float(str(cleaned_data['NO'])))
            except (ValueError, TypeError):
                cleaned_data['NO'] = 1
        
        return cleaned_data

    @staticmethod
    def transform_ppm_entry(flat_entry: dict) -> dict:
        """Transform flat PPM entry to nested structure."""
        # Helper function to convert N/A to None
        def clean_value(value):
            if value is None or (isinstance(value, str) and (value.strip() == '' or value.strip().upper() == 'N/A')):
                return None
            return value
        
        result = {
            "Department": flat_entry.get("Department"),
            "Name": flat_entry.get("Name"),
            "MODEL": flat_entry.get("MODEL"),
            "SERIAL": flat_entry.get("SERIAL"),
            "MANUFACTURER": flat_entry.get("MANUFACTURER"),
            "LOG_Number": flat_entry.get("LOG_Number"),
            "Installation_Date": clean_value(flat_entry.get("Installation_Date")),
            "Warranty_End": clean_value(flat_entry.get("Warranty_End")),
        }

        # Convert flat quarter fields to nested QuarterData objects
        for quarter in ["I", "II", "III", "IV"]:
            date_key = f"PPM_Q_{quarter}_date"
            eng_key = f"PPM_Q_{quarter}_engineer"
            result[f"PPM_Q_{quarter}"] = {
                "quarter_date": flat_entry.get(date_key),
                "engineer": flat_entry.get(eng_key)
            }

        # Calculate missing quarter dates if Q1 is provided
        if flat_entry.get("PPM_Q_I_date"):
            q1_date = datetime.strptime(flat_entry["PPM_Q_I_date"], "%d/%m/%Y")
            for i, quarter in enumerate(["II", "III", "IV"], start=1):
                if not flat_entry.get(f"PPM_Q_{quarter}_date"):
                    next_date = q1_date + timedelta(days=90 * i)
                    result[f"PPM_Q_{quarter}"]["quarter_date"] = next_date.strftime("%d/%m/%Y")

        # Add initial status
        result["Status"] = "Upcoming"
        
        return result
