"""
Service for importing and exporting data.
"""
import logging
import os
from io import StringIO
from typing import List, Dict, Any, Literal, Tuple
import json

import pandas as pd
from pydantic import ValidationError

from app.models.ppm import PPMImportEntry
from app.models.ocm import OCMEntry
from app.services.data_service import DataService


logger = logging.getLogger('app')
logger.debug("Initializing import/export service")

class ImportExportService:
    """Service for handling import and export operations."""
    
    @staticmethod
    def detect_csv_type(columns: List[str]) -> Literal['ppm', 'ocm', 'unknown']:
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
        
        ocm_required = {
            'Department',
            'Name',
            'Model',
            'Serial',
            'Manufacturer',
            'Log Number',
            'Installation Date',
            'Service Date',
            'Next Maintenance'
        }
        
        print(f"OCM required columns: {sorted(ocm_required)}")
        missing_ocm = ocm_required - columns_set
        if missing_ocm:
            print(f"Missing OCM columns: {sorted(missing_ocm)}")
            for col in missing_ocm:
                print(f"Looking for '{col}' in available columns:")
                print([c for c in columns_set if col.lower() in c.lower()])
        
        if ppm_required.issubset(columns_set):
            return 'ppm'
        elif ocm_required.issubset(columns_set):
            return 'ocm'
        return 'unknown'

    @staticmethod
    def export_to_csv(data_type: Literal['ppm', 'ocm'], output_path: str = None) -> Tuple[bool, str, str]:
        """Export data to CSV file.
        
        Args:
            data_type: Type of data to export ('ppm' or 'ocm')
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
                logger.debug(f"Processing entry {idx + 1}/{len(data)} with SERIAL: {entry.get('SERIAL') if data_type == 'ppm' else entry.get('Serial')}")
                
                if data_type == 'ppm':
                    # PPM export handling (existing code)
                    flat_entry = {
                        'NO': entry.get('NO'),
                        'Department': entry.get('Department'),
                        'Name': entry.get('Name'),
                        'MODEL': entry.get('MODEL'),
                        'SERIAL': entry.get('SERIAL'),
                        'MANUFACTURER': entry.get('MANUFACTURER'),
                        'LOG_Number': entry.get('LOG_Number'),
                        'Installation_date:': entry.get('Installation_Date'),
                        'Warranty_end': entry.get('Warranty_End')
                    }
                    
                    quarter_map = [
                        ('I', 'PPM_Q_I'),
                        ('II', 'PPM_Q_II'),
                        ('III', 'PPM_Q_III'),
                        ('IV', 'PPM_Q_IV')
                    ]
                    
                    for roman, q_key in quarter_map:
                        q_data = entry.get(q_key, {})
                        flat_entry[f'PPM_Q_{roman}_date'] = q_data.get('quarter_date', '')
                        flat_entry[f'PPM_Q_{roman}_engineer'] = q_data.get('engineer', '')
                    
                else:  # OCM export handling
                    flat_entry = {
                        'NO': entry.get('NO'),
                        'Department': entry.get('Department'),
                        'Name': entry.get('Name'),
                        'Model': entry.get('Model'),
                        'Serial': entry.get('Serial'),
                        'Manufacturer': entry.get('Manufacturer'),
                        'Log Number': entry.get('Log Number'),
                        'Installation Date': entry.get('Installation Date'),
                        'Warranty End': entry.get('Warranty End'),
                        'Service Date': entry.get('Service Date'),
                        'Engineer': entry.get('Engineer'),
                        'Next Maintenance': entry.get('Next Maintenance'),
                        'Status': entry.get('Status')
                    }
                
                flat_entry['Status'] = entry.get('Status', '')
                flat_data.append(flat_entry)
            
            df = pd.DataFrame(flat_data)
            
            # Ensure NO is always first column
            if 'NO' in df.columns:
                cols = ['NO'] + [col for col in df.columns if col != 'NO']
                df = df[cols]
            
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
    def import_from_csv(data_type: Literal['ppm', 'ocm'], file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Import data from CSV file.
        
        Args:
            data_type: Type of data to import ('ppm' or 'ocm')
            file_path: Path to CSV file
            
        Returns:
            Tuple of (success, message, import_stats)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}", {}

            # Read CSV
            df = pd.read_csv(file_path)
            df.fillna('', inplace=True)
            df = df.astype(str)

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
                    'Warranty End': 'Warranty_End',
                    'Next Maintenance': 'Next_Maintenance'
                }
                # Rename columns to match model field names
                df = df.rename(columns=column_mapping)
                logger.debug(f"Renamed columns: {df.columns.tolist()}")

            current_data = DataService.load_data(data_type)
            serial_key = 'SERIAL' if data_type == 'ppm' else 'Serial'
            existing_serials = {entry.get(serial_key) for entry in current_data}
            
            # Process rows
            new_entries = []
            skipped_entries = []
            error_entries = []
            
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                logger.debug(f"Processing row {idx + 1}: {row_dict}")
                
                try:
                    # Remove NO field if present, it will be reassigned
                    row_dict.pop('NO', None)
                    
                    # Check for duplicate serial
                    if row_dict[serial_key] in existing_serials:
                        logger.warning(f"Skipping row {idx + 1}: Duplicate {serial_key} number {row_dict[serial_key]}")
                        skipped_entries.append(f"Row {idx + 1}: Duplicate {serial_key} number {row_dict[serial_key]}")
                        continue
                    
                    if data_type == 'ppm':
                        # Handle PPM data
                        entry = PPMImportEntry(**row_dict)
                    else:
                        # Add NO field for OCM entries
                        row_dict['NO'] = idx + 1
                        # Handle OCM data
                        entry = OCMEntry(**row_dict)
                    
                    validated_entry = entry.model_dump()
                    logger.debug(f"Successfully validated row {idx + 1}")
                    new_entries.append(validated_entry)
                    existing_serials.add(row_dict[serial_key])
                    
                except ValidationError as ve:
                    logger.error(f"Validation error in row {idx + 1}: {str(ve)}")
                    error_entries.append(f"Row {idx + 1}: Validation error - {str(ve)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing row {idx + 1}: {str(e)}")
                    error_entries.append(f"Row {idx + 1}: {str(e)}")
                    continue
            
            if new_entries:
                # Add entries and reindex
                current_data.extend(new_entries)
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
