"""
Data service for managing equipment maintenance data.
"""
import json
import logging
import io
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, Union, TextIO, get_args
from datetime import datetime, date, timedelta

from dateutil.relativedelta import relativedelta
import pandas as pd
from pydantic import ValidationError

from app.config import Config
from app.models.ppm import PPMEntry
from app.models.ocm import OCMEntry


logger = logging.getLogger(__name__)


class DataService:
    """Service for managing equipment maintenance data."""
    @staticmethod
    def ensure_data_files_exist():
        """Ensure data directory and files exist."""
        logger.debug("Ensuring data files exist")
        data_dir = Path(Config.DATA_DIR)
        logger.debug(f"Using data directory: {data_dir}")
        data_dir.mkdir(exist_ok=True)

        ppm_path = Path(Config.PPM_JSON_PATH)
        ocm_path = Path(Config.OCM_JSON_PATH)

        logger.debug(f"Checking PPM data file: {ppm_path}")
        if not ppm_path.exists():
            logger.info(f"Creating new PPM data file: {ppm_path}")
            with open(ppm_path, 'w') as f:
                json.dump([], f)

        logger.debug(f"Checking OCM data file: {ocm_path}")
        if not ocm_path.exists():
            logger.info(f"Creating new OCM data file: {ocm_path}")
            with open(ocm_path, 'w') as f:
                json.dump([], f)

    @staticmethod
    def load_data(data_type: Literal['ppm', 'ocm']) -> List[Dict[str, Any]]:
        """Load data from JSON file.

        Args:
            data_type: Type of data to load ('ppm' or 'ocm')

        Returns:
            List of data entries
        """
        logger.debug("Starting load_data method with data_type='%s'", data_type)

        try:
            logger.debug("Calling DataService.ensure_data_files_exist()")
            DataService.ensure_data_files_exist()

            logger.debug("Determining file path based on data_type")
            if data_type == 'ppm':
                file_path = Config.PPM_JSON_PATH
                logger.debug("Selected PPM file path: %s", file_path)
            else:
                file_path = Config.OCM_JSON_PATH
                logger.debug("Selected OCM file path: %s", file_path)

            logger.debug("Opening file for reading: %s", file_path)
            with open(file_path, 'r') as f:
                logger.debug("Reading content from file: %s", file_path)
                content = f.read()

                logger.debug("Checking if file content is empty")
                if not content:
                    logger.debug("File is empty. Returning an empty list.")
                    return []

                logger.debug("Attempting to decode JSON content")
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from {file_path}: {str(e)}. Returning empty list.")
                    return []

                logger.debug("Successfully decoded JSON. Data type: %s", type(data))
                logger.debug("Loaded data sample (first 2 items): %s", data[:2] if isinstance(data, list) else data)

                logger.debug("Returning loaded data with %d entries", len(data) if isinstance(data, list) else 0)
                return data

        except FileNotFoundError:
            logger.warning(f"Data file {file_path} not found. Returning empty list.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading {data_type} data from {file_path}: {str(e)}. Returning empty list.")
            return []
    
    @staticmethod
    def save_data(data: List[Dict[str, Any]], data_type: Literal['ppm', 'ocm']):
        """Save data to JSON file.

        Args:
            data: List of data entries to save
            data_type: Type of data to save ('ppm' or 'ocm')
        """
        try:
            DataService.ensure_data_files_exist()

            file_path = Config.PPM_JSON_PATH if data_type == 'ppm' else Config.OCM_JSON_PATH
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"IOError saving {data_type} data to {file_path}: {str(e)}")
            # Potentially re-raise a custom exception or handle as critical
            raise ValueError(f"Failed to save {data_type} data due to IO error.") from e
        except Exception as e:
            logger.error(f"Unexpected error saving {data_type} data to {file_path}: {str(e)}")
            raise ValueError(f"Failed to save {data_type} data due to an unexpected error.") from e

    @staticmethod
    def calculate_status(entry_data: Dict[str, Any], data_type: Literal['ppm', 'ocm']) -> Literal["Upcoming", "Overdue", "Maintained"]:
        """
        Calculates the status of a PPM or OCM entry.
        """
        today = datetime.now().date()

        if data_type == 'ppm':
            # For PPM, status is based on Eng1-4 fields.
            # This is a simplified interpretation: if all Eng fields for past/current quarters are filled, it's Maintained.
            # A more precise calculation would need actual quarter dates.
            # Assuming EngX fields imply work done for that quarter.
            # For PPM, status is based on PPM_Q_I to PPM_Q_IV fields, specifically their 'quarter_date' and 'engineer'.
            today_date = datetime.now().date()
            is_overdue = False
            maintained_quarters_count = 0
            past_due_quarters_with_engineer = 0
            total_past_due_quarters = 0

            for q_key in ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']:
                quarter_info = entry_data.get(q_key, {})
                if not isinstance(quarter_info, dict): # Should be a dict after model validation
                    quarter_info = {}

                quarter_date_str = quarter_info.get('quarter_date')
                engineer_name = quarter_info.get('engineer')

                if not quarter_date_str:
                    # If no date, this quarter cannot make it overdue by itself,
                    # but lack of engineer might contribute to "Upcoming" if no other action.
                    continue

                try:
                    current_quarter_date = datetime.strptime(quarter_date_str, '%d/%m/%Y').date()
                except ValueError:
                    logger.warning(f"Invalid quarter_date format for {entry_data.get('SERIAL')}, quarter {q_key}: {quarter_date_str}")
                    continue # Skip this quarter for status calculation if date is invalid

                if current_quarter_date < today_date:
                    total_past_due_quarters += 1
                    if engineer_name and engineer_name.strip():
                        past_due_quarters_with_engineer += 1
                    else:
                        is_overdue = True # Found a past due quarter without an engineer

                # For "Maintained" status, we count quarters with an engineer, irrespective of date for now.
                # Refinement: "Maintained" typically means past services are done.
                if engineer_name and engineer_name.strip():
                    maintained_quarters_count +=1


            if is_overdue:
                return "Overdue"

            # If all past due quarters have an engineer, and there was at least one such quarter
            if total_past_due_quarters > 0 and past_due_quarters_with_engineer == total_past_due_quarters:
                return "Maintained"

            # If there are no past due quarters, and some future quarters might or might not have engineers
            # or if all past due quarters are maintained, but there are future quarters.
            if not total_past_due_quarters and maintained_quarters_count > 0 : # e.g. all future but one is assigned
                 # This could still be upcoming if all assigned quarters are in the future
                 # Let's refine "Maintained": if all *past* quarters are done, and there are future ones.
                 # The existing logic: if not overdue, and past_due_quarters_with_engineer == total_past_due_quarters
                 # this covers the case where past work is done. If total_past_due_quarters is 0, it's upcoming.
                 pass # Fall through to Upcoming

            # If no quarters were overdue, and no past quarters were "maintained" (e.g. all future, or past but no engineer which means overdue)
            # Default to upcoming if not Overdue and not clearly Maintained (all past work done)
            return "Upcoming"

        elif data_type == 'ocm':
            next_maintenance_str = entry_data.get("Next_Maintenance")
            service_date_str = entry_data.get("Service_Date") # Assuming Service_Date means it was maintained

            if not next_maintenance_str:
                return "Upcoming" # Or some other default if no maintenance date

            try:
                next_maintenance_date = datetime.strptime(next_maintenance_str, '%d/%m/%Y').date()
            except ValueError:
                logger.warning(f"Invalid Next_Maintenance date format for {entry_data.get('SERIAL')}: {next_maintenance_str}")
                return "Upcoming" # Default status if date is invalid

            # If there's a service date, and it's on or after the next maintenance, consider it Maintained.
            # Or if service date is recent enough (e.g. within the last year, assuming annual cycle).
            # This logic can be complex.
            if service_date_str:
                try:
                    service_date = datetime.strptime(service_date_str, '%d/%m/%Y').date()
                    # Example: Maintained if serviced after or on the next maintenance due date,
                    # or if serviced recently (e.g. within the last maintenance cycle period if known)
                    if service_date >= next_maintenance_date: # This might not be the right condition
                        return "Maintained"
                    # A more robust check: if service_date is after the *previous* theoretical maintenance date
                    # and before or on the *next* one.
                    # For simplicity now: if Next_Maintenance is in future, and we had a service date,
                    # it's complex to know if it's "Maintained" for the *next* cycle yet.
                    # Let's assume if Next_Maintenance is in the future, it's "Upcoming" unless service date is very recent.
                except ValueError:
                    logger.warning(f"Invalid Service_Date format for {entry_data.get('SERIAL')}: {service_date_str}")

            if next_maintenance_date < today:
                return "Overdue"
            else:
                return "Upcoming"

        return "Upcoming" # Default fallback

    @staticmethod
    def _calculate_ppm_quarter_dates(installation_date_str: Optional[str]) -> List[Optional[str]]:
        """
        Calculates four quarterly PPM dates.
        Q1 is 3 months after installation_date_str or today if not provided/invalid.
        Q2, Q3, Q4 are 3 months after the previous quarter.
        Returns dates as DD/MM/YYYY strings.
        """
        base_date = None
        if installation_date_str:
            try:
                base_date = datetime.strptime(installation_date_str, '%d/%m/%Y').date()
            except ValueError:
                logger.warning(f"Invalid Installation_Date format '{installation_date_str}'. Using today for PPM quarter calculation.")
                base_date = datetime.today().date()
        else:
            base_date = datetime.today().date()

        q_dates = []
        current_q_date = base_date
        for _ in range(4):
            current_q_date += relativedelta(months=3)
            q_dates.append(current_q_date.strftime('%d/%m/%Y'))
        return q_dates

    @staticmethod
    def _ensure_unique_serial(data: List[Dict[str, Any]], new_entry: Dict[str, Any], data_type: Literal['ppm', 'ocm'], exclude_serial: Optional[str] = None):
        """Ensure Serial/SERIAL is unique in the data."""
        serial_key = 'SERIAL' if data_type == 'ppm' else 'Serial'
        serial = new_entry.get(serial_key)
        if not serial:
            raise ValueError(f"{serial_key} cannot be empty.")

        if exclude_serial and serial == exclude_serial:
            return

        count = sum(1 for entry in data if entry.get(serial_key) == serial)
        if count >= 1:
            raise ValueError(f"Duplicate {serial_key} detected: {serial}")

    @staticmethod
    def reindex(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reindex entries after deletion or reordering.
        
        Args:
            data: List of entries to reindex
            
        Returns:
            List of reindexed entries
        """
        logger.debug(f"Reindexing {len(data)} entries")
        for i, entry in enumerate(data, start=1):
            entry['NO'] = i
            logger.debug(f"Set NO={i} for entry with Serial/SERIAL: {entry.get('Serial', entry.get('SERIAL'))}")
        return data    @staticmethod
    def _reindex_entries(entries):
        """Reindex entries after import or deletion."""
        for idx, entry in enumerate(entries, start=1):
            entry['NO'] = idx
        return entries

    @staticmethod
    def add_entry(data_type: Literal['ppm', 'ocm'], entry: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new entry to the data.
        
        Args:
            data_type: Type of data to add entry to ('ppm' or 'ocm')
            entry: Entry data to add
            
        Returns:
            Added entry with assigned NO
        """
        logger.debug("Starting add_entry function.")
        logger.debug(f"Received data_type: {data_type}")
        logger.debug(f"Received entry: {entry}")

        try:
            # Create copy of entry to avoid modifying original
            entry_copy = entry.copy()
            logger.debug(f"Created copy of entry: {entry_copy}")

            # Remove NO if present (we'll calculate it)
            entry_copy.pop('NO', None)
            logger.debug(f"After removing 'NO': {entry_copy}")

            # Load existing data to calculate new NO
            all_data = DataService.load_data(data_type)
            new_no = len(all_data) + 1
            logger.debug(f"Calculated new NO: {new_no}")

            # Add NO to entry_copy before validation
            entry_copy['NO'] = new_no
            logger.debug(f"Added NO to entry: {entry_copy}")

            if 'Status' in entry_copy:
                logger.debug(f"Using provided Status: {entry_copy['Status']}")
            else:
                # Default Status handling if needed
                pass

            # Process and validate the entry
            if data_type == 'ppm':
                logger.debug("Processing PPM entry...")
                # PPM specific processing
                if isinstance(entry_copy.get('Status'), str) and not entry_copy['Status'].strip():
                    entry_copy['Status'] = None

                # Process PPM quarter fields
                for quarter_key in ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']:
                    if isinstance(entry_copy.get(quarter_key), str):
                        entry_copy[quarter_key] = {
                            'engineer': entry_copy[quarter_key]
                        }
                    elif isinstance(entry_copy.get(quarter_key), dict):
                        entry_copy[quarter_key].setdefault('engineer', None)
                        logger.debug(f"Ensured 'engineer' key in {quarter_key}: {entry_copy[quarter_key]}")

                logger.debug(f"Final entry_copy before PPM validation: {entry_copy}")
                validated_entry_model = PPMEntry(**entry_copy)
            else:
                logger.debug("Processing OCM entry...")
                logger.debug(f"Final entry_copy before OCM validation: {entry_copy}")
                validated_entry_model = OCMEntry(**entry_copy)

            validated_entry = validated_entry_model.model_dump()
            logger.debug(f"Validated entry after model dump: {validated_entry}")

            # Ensure serial is unique
            DataService._ensure_unique_serial(all_data, validated_entry, data_type)

            # Add to data
            all_data.append(validated_entry)
            logger.debug(f"Added entry to data. New total: {len(all_data)}")

            # Save updated data
            DataService.save_data(all_data, data_type)
            logger.info(f"Successfully added new {data_type} entry with NO: {new_no}")

            return validated_entry

        except ValidationError as e:
            logger.error(f"Validation error adding {data_type} entry: {str(e)}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Error adding {data_type} entry: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def update_entry(data_type: Literal['ppm', 'ocm'], serial: str, updated_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing entry.

        Args:
            data_type: Type of data to update ('ppm' or 'ocm')
            serial: Serial number of entry to update
            updated_data: New data for the entry

        Returns:
            Updated entry if successful, None if entry not found

        Raises:
            ValueError: If validation fails
        """
        logger.info(f"Attempting to update {data_type} entry with serial: {serial}")
        logger.debug(f"Update data received: {updated_data}")

        try:
            # Load all data
            logger.debug(f"Loading all {data_type} data to find entry with serial {serial}")
            data = DataService.load_data(data_type)
            
            # Find and update the entry
            found = False
            for i, entry in enumerate(data):
                entry_serial = entry.get('Serial', entry.get('SERIAL'))
                logger.debug(f"Comparing entry serial '{entry_serial}' with update serial '{serial}'")
                
                if entry_serial == serial:
                    logger.info(f"Found matching {data_type} entry to update")
                    logger.debug(f"Original entry data: {entry}")
                    
                    # Preserve required fields if not in updated_data
                    if data_type == 'ocm' and 'NO' not in updated_data and 'NO' in entry:
                        logger.debug(f"Preserving NO field from original entry: {entry['NO']}")
                        updated_data['NO'] = entry['NO']
                    
                    # Validate updated data
                    logger.debug(f"Validating updated data for {data_type}: {updated_data}")
                    try:
                        if data_type == 'ppm':
                            # If 'Status' is not in updated_data and 'Status' is in the original entry,
                            # preserve the original 'Status'.
                            if 'Status' not in updated_data and 'Status' in entry:
                                updated_data['Status'] = entry['Status']
                            PPMEntry(**updated_data)
                        else:
                            OCMEntry(**updated_data)
                        logger.debug("Data validation successful")
                    except ValidationError as e:
                        logger.error(f"Validation error for {data_type} update: {str(e)}")
                        raise ValueError(f"Invalid {data_type.upper()} data: {str(e)}")
                    
                    # Update the entry
                    data[i] = updated_data
                    found = True
                    logger.debug(f"Updated entry data: {updated_data}")
                    break
            
            if not found:
                logger.warning(f"No {data_type} entry found with serial {serial} for update")
                return None
            
            # Save the updated data
            logger.info(f"Saving updated {data_type} data")
            DataService.save_data(data, data_type)
            
            logger.info(f"Successfully updated {data_type} entry with serial {serial}")
            return updated_data

        except Exception as e:
            logger.error(f"Error updating {data_type} entry with serial {serial}: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def delete_entry(data_type: Literal['ppm', 'ocm'], SERIAL: str) -> bool:
        """Delete an entry.

        Args:
            data_type: Type of data to delete entry from ('ppm' or 'ocm')
            SERIAL: SERIAL of entry to delete

        Returns:
            True if entry was deleted, False if not found
        """
        logger.info(f"Attempting to delete {data_type} entry with serial: {SERIAL}")
        
        try:
            data = DataService.load_data(data_type)
            initial_len = len(data)
            logger.debug(f"Loaded {initial_len} entries from {data_type} data")
            
            # Handle different serial field names for PPM and OCM
            serial_field = 'SERIAL' if data_type == 'ppm' else 'Serial'
            logger.debug(f"Using serial field name: {serial_field}")
            
            # Find the entry to delete first
            entry_to_delete = None
            entry_index = -1
            
            for i, entry in enumerate(data):
                entry_serial = entry.get(serial_field)
                logger.debug(f"Comparing entry serial '{entry_serial}' with target serial '{SERIAL}'")
                if entry_serial == SERIAL:
                    entry_to_delete = entry
                    entry_index = i
                    break
            
            if entry_to_delete is None:
                logger.warning(f"No {data_type} entry found with serial {SERIAL}")
                return False
                
            logger.info(f"Found {data_type} entry to delete: {entry_to_delete}")
            
            # Remove the entry
            data.pop(entry_index)
            logger.debug(f"Removed entry at index {entry_index}")
            
            # Reindex the remaining entries
            reindexed_data = DataService.reindex(data)
            logger.debug(f"Reindexed remaining {len(reindexed_data)} entries")
            
            # Save the updated data
            DataService.save_data(reindexed_data, data_type)
            logger.info(f"Successfully deleted {data_type} entry with serial {SERIAL}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting {data_type} entry with serial {SERIAL}: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_entry(data_type: Literal['ppm', 'ocm'], serial: str) -> Optional[Dict[str, Any]]:
        """Get a single entry by serial number.

        Args:
            data_type: Type of data to search ('ppm' or 'ocm')
            serial: Serial number to search for

        Returns:
            Entry if found, None otherwise
        """
        logger.info(f"Attempting to get {data_type} entry with serial: {serial}")
        try:
            # Load all data
            logger.debug(f"Loading all {data_type} data to search for serial {serial}")
            data = DataService.load_data(data_type)
            
            # Find entry with matching serial
            logger.debug(f"Searching for entry with serial {serial} in {len(data)} {data_type} entries")
            for entry in data:
                entry_serial = entry.get('Serial', entry.get('SERIAL'))  # Handle both field names
                logger.debug(f"Comparing entry serial '{entry_serial}' with search serial '{serial}'")
                if entry_serial == serial:
                    logger.info(f"Found matching {data_type} entry for serial {serial}")
                    logger.debug(f"Entry data: {entry}")
                    return entry
            
            logger.warning(f"No {data_type} entry found with serial {serial}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving {data_type} entry with serial {serial}: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_all_entries(data_type: Literal['ppm', 'ocm']) -> List[Dict[str, Any]]:
        """Get all entries.

        Args:
            data_type: Type of data to get entries from ('ppm' or 'ocm')

        Returns:
            List of all entries
        """
        return DataService.load_data(data_type)

    @staticmethod
    def import_data(data_type: Literal['ppm', 'ocm'], file_stream: TextIO) -> Dict[str, Any]:
        """
        Bulk import data from a CSV file stream.
        'NO' field in CSV is ignored. SERIAL uniqueness is enforced by replacing existing.
        Status is calculated if not provided or invalid.
        """
        logger.info(f"Starting bulk import for data type: {data_type}")
        added_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        try:
            logger.debug("Reading CSV file with pandas")
            df = pd.read_csv(file_stream, dtype=str)
            df.fillna('', inplace=True)
            logger.debug(f"CSV columns found: {', '.join(df.columns)}")

            if 'SERIAL' not in df.columns:
                error_msg = "CSV file missing required SERIAL column"
                logger.error(error_msg)
                errors.append(error_msg)
                return {"errors": errors}

            if data_type == 'ppm':
                logger.debug("Processing PPM data")
                # Define expected CSV columns for PPM import
                expected_columns = ['MODEL', 'SERIAL', 'MANUFACTURER', 'Department']
                missing_columns = [col for col in expected_columns if col not in df.columns]
                if missing_columns:
                    error_msg = f"Missing required columns for PPM: {', '.join(missing_columns)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    return {"errors": errors}
            else:  # ocm
                logger.debug("Processing OCM data")
                expected_columns = ['MODEL', 'SERIAL', 'MANUFACTURER', 'Service_Date']
                missing_columns = [col for col in expected_columns if col not in df.columns]
                if missing_columns:
                    error_msg = f"Missing required columns for OCM: {', '.join(missing_columns)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    return {"errors": errors}

            logger.info(f"Found {len(df)} rows to process")
            current_data = DataService.load_data(data_type)
            logger.debug(f"Loaded {len(current_data)} existing records")
            current_data_map = {entry.get('SERIAL'): entry for entry in current_data}

            processed_data = current_data.copy()  # Start with existing data

            for index, row in df.iterrows():
                try:
                    logger.debug(f"Processing row {index + 1}/{len(df)}")
                    serial = row.get('SERIAL', '').strip()
                    
                    if not serial:
                        logger.warning(f"Skipping row {index + 1}: Empty SERIAL")
                        skipped_count += 1
                        errors.append(f"Row {index + 1}: Empty SERIAL")
                        continue
                    
                    entry_data = row.to_dict()
                    entry_data = {k: str(v).strip() if isinstance(v, str) else v for k, v in entry_data.items()}
                      # First get the Q1 date to base other quarters on
                    q1_date = entry_data.get("PPM_Q_I.date", "")
                    base_date = None
                    if q1_date:
                        try:
                            base_date = datetime.strptime(q1_date, '%d/%m/%Y').date()
                        except ValueError:
                            logger.warning(f"Invalid Q1 date format: {q1_date}")
                            base_date = None
                    
                    if not base_date:
                        # If no valid Q1 date, fall back to installation date or current date
                        installation_date = entry_data.get("Installation_Date", "")
                        if installation_date:
                            try:
                                base_date = datetime.strptime(installation_date, '%d/%m/%Y').date()
                            except ValueError:
                                base_date = datetime.now().date()
                        else:
                            base_date = datetime.now().date()

                    # Calculate quarter dates based on Q1 date
                    q_dates = []
                    current_date = base_date
                    for _ in range(4):
                        if not q_dates:  # First quarter uses actual Q1 date if available
                            q_dates.append(q1_date if q1_date else current_date.strftime('%d/%m/%Y'))
                        else:
                            current_date += relativedelta(months=3)
                            q_dates.append(current_date.strftime('%d/%m/%Y'))

                    # Transform the data to match PPM structure, starting with NO
                    transformed_entry = {
                        "NO": len(processed_data) + 1,  # Add NO at the beginning
                        "Department": entry_data.get("Department", ""),
                        "Name": entry_data.get("Name", ""),
                        "MODEL": entry_data.get("MODEL", ""),
                        "SERIAL": serial,
                        "MANUFACTURER": entry_data.get("MANUFACTURER", ""),
                        "LOG_Number": entry_data.get("LOG_Number", ""),
                        "Installation_Date": entry_data.get("Installation_Date", ""),
                        "Warranty_End": entry_data.get("Warranty_End", "")
                    }

                    # Process PPM quarters
                    transformed_entry["PPM_Q_I"] = {
                        "engineer": entry_data.get("PPM_Q_I.engineer", ""),
                        "quarter_date": q_dates[0]
                    }
                    transformed_entry["PPM_Q_II"] = {
                        "engineer": entry_data.get("PPM_Q_II.engineer", ""),
                        "quarter_date": q_dates[1]
                    }
                    transformed_entry["PPM_Q_III"] = {
                        "engineer": entry_data.get("PPM_Q_III.engineer", ""),
                        "quarter_date": q_dates[2]
                    }
                    transformed_entry["PPM_Q_IV"] = {
                        "engineer": entry_data.get("PPM_Q_IV.engineer", ""),
                        "quarter_date": q_dates[3]
                    }
                    
                    # Calculate Status if not present
                    transformed_entry["Status"] = entry_data.get("Status") or DataService.calculate_status(transformed_entry, data_type)

                    if serial in current_data_map:
                        # Update existing record
                        for i, entry in enumerate(processed_data):
                            if entry.get('SERIAL') == serial:
                                processed_data[i].update(transformed_entry)
                                break
                        logger.debug(f"Updated existing record for SERIAL: {serial}")
                        updated_count += 1
                    else:
                        # Add new record with NO field
                        transformed_entry["NO"] = len(processed_data) + 1
                        processed_data.append(transformed_entry)
                        logger.debug(f"Added new record for SERIAL: {serial}")
                        added_count += 1

                except Exception as row_error:
                    error_msg = f"Error processing row {index + 1}: {str(row_error)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    skipped_count += 1

            # Save the updated data back to the JSON file
            DataService.save_data(processed_data, data_type)

            logger.info(f"Import complete. Added: {added_count}, Updated: {updated_count}, Skipped: {skipped_count}")
            if errors:
                logger.warning(f"Import completed with {len(errors)} errors")

            return {
                "added_count": added_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
                "errors": errors
            }

        except Exception as e:
            error_msg = f"Error during import: {str(e)}"
            logger.exception(error_msg)
            errors.append(error_msg)
            return {
                "added_count": added_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
                "errors": errors
            }
    @classmethod
    def export_data(cls, data_type: Literal['ppm', 'ocm']) -> str:
        """Export data to CSV format."""
        logger.debug(f"DataService.export_data called for {data_type}")
        try:
            # Load data from appropriate file
            data = cls.load_data(data_type)
            logger.debug(f"Loaded {len(data) if data else 0} entries for export")
            
            if not data:
                logger.warning(f"No {data_type} data available for export")
                return ""

            # Convert data for export
            from app.services.import_export import ImportExportService
            logger.debug(f"Calling ImportExportService.export_to_csv for {data_type}")
            success, message, csv_content = ImportExportService.export_to_csv(data_type)
            
            if not success:
                logger.error(f"Export failed: {message}")
                return ""
                
            logger.debug(f"Export successful. CSV content length: {len(csv_content)} bytes")
            logger.debug(f"First 200 characters of CSV: {csv_content[:200]}")
            return csv_content
            
        except Exception as e:
            logger.exception(f"Error in export_data for {data_type}: {str(e)}")
            raise
