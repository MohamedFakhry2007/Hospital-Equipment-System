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
        data_dir = Path(Config.DATA_DIR)
        data_dir.mkdir(exist_ok=True)

        ppm_path = Path(Config.PPM_JSON_PATH)
        ocm_path = Path(Config.OCM_JSON_PATH)

        if not ppm_path.exists():
            with open(ppm_path, 'w') as f:
                json.dump([], f)

        if not ocm_path.exists():
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
        try:
            DataService.ensure_data_files_exist()

            file_path = Config.PPM_JSON_PATH if data_type == 'ppm' else Config.OCM_JSON_PATH
            with open(file_path, 'r') as f:
                # Handle empty file case
                content = f.read()
                if not content:
                    return []

                data = json.loads(content)
                # Validate each entry against the respective model
                # This helps catch data inconsistencies early
                Model = PPMEntry if data_type == 'ppm' else OCMEntry
                validated_data = []
                for entry_dict in data:
                    try:
                        Model(**entry_dict) # Validate
                        validated_data.append(entry_dict) # Add if valid
                    except ValidationError as ve:
                        logger.warning(f"Data validation error loading {data_type} entry {entry_dict.get('MFG_SERIAL', 'N/A')}: {ve}. Skipping this entry.")
                return validated_data

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {file_path}: {str(e)}. Returning empty list.")
            return []
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
                    logger.warning(f"Invalid quarter_date format for {entry_data.get('MFG_SERIAL')}, quarter {q_key}: {quarter_date_str}")
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
                logger.warning(f"Invalid Next_Maintenance date format for {entry_data.get('MFG_SERIAL')}: {next_maintenance_str}")
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
                    logger.warning(f"Invalid Service_Date format for {entry_data.get('MFG_SERIAL')}: {service_date_str}")

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
    def ensure_unique_mfg_serial(data: List[Dict[str, Any]], new_entry: Dict[str, Any], exclude_serial: Optional[str] = None):
        """Ensure MFG_SERIAL is unique in the data.

        Args:
            data: Current data list
            new_entry: New entry to add or check
            exclude_serial: Serial to exclude from check (for updates)

        Raises:
            ValueError: If MFG_SERIAL is not unique
        """
        mfg_serial = new_entry.get('MFG_SERIAL')
        if not mfg_serial:
             raise ValueError("MFG_SERIAL cannot be empty.")

        # If exclude_serial is provided (during update), skip check if serial matches
        if exclude_serial and mfg_serial == exclude_serial:
            return

        # Check against existing data
        count = sum(1 for entry in data if entry.get('MFG_SERIAL') == mfg_serial)
        if count >= 1:
            raise ValueError(f"Duplicate MFG_SERIAL detected: {mfg_serial}")


    @staticmethod
    def reindex(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reindex data entries. Adds 'NO' field sequentially.

        Args:
            data: List of data entries

        Returns:
            Reindexed list of data entries
        """
        for i, entry in enumerate(data, start=1):
            entry['NO'] = i
        return data

    @staticmethod
    def add_entry(data_type: Literal['ppm', 'ocm'], entry: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new entry to the data.

        Args:
            data_type: Type of data to add entry to ('ppm' or 'ocm')
            entry: Entry to add

        Returns:
            Added entry with NO assigned

        Raises:
            ValueError: If entry is invalid or MFG_SERIAL is not unique
        """
        entry_copy = entry.copy()
        entry_copy.pop('NO', None) # Remove 'NO' as it's managed internally

        # Calculate status before validation if Status is not provided or needs recalculation
        # The model now has Status, so it should be part of entry_copy or calculated.
        # If status is provided in `entry`, it will be used, otherwise calculate.
        if 'Status' not in entry_copy or entry_copy['Status'] is None:
             entry_copy['Status'] = DataService.calculate_status(entry_copy, data_type)

        try:
            if data_type == 'ppm':
                # Populate quarter dates before validation
                installation_date_str = entry_copy.get('Installation_Date')
                q_dates = DataService._calculate_ppm_quarter_dates(installation_date_str)
                for i, q_key in enumerate(['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']):
                    # entry_copy from PPMEntryCreate has PPM_Q_X as Dict[str, str] e.g. {"engineer": "name"}
                    # We need to add quarter_date to it.
                    quarter_data_dict = entry_copy.get(q_key, {})
                    if not isinstance(quarter_data_dict, dict): # Ensure it's a dictionary
                        quarter_data_dict = {} # Initialize if not present or wrong type
                    quarter_data_dict['quarter_date'] = q_dates[i]
                    entry_copy[q_key] = quarter_data_dict

                validated_entry_model = PPMEntry(**entry_copy)
            else:
                validated_entry_model = OCMEntry(**entry_copy)
            validated_entry = validated_entry_model.model_dump()
        except ValidationError as e:
            logger.error(f"Validation error adding {data_type} entry: {str(e)}")
            # Propagate a more user-friendly error message
            raise ValueError(f"Invalid {data_type.upper()} entry data: {e}") from e

        all_data = DataService.load_data(data_type)
        DataService.ensure_unique_mfg_serial(all_data, validated_entry)

        all_data.append(validated_entry)
        reindexed_data = DataService.reindex(all_data)
        DataService.save_data(reindexed_data, data_type)

        # Return the added entry (it's the last one after reindexing if no error)
        # Find by MFG_SERIAL to be sure
        for e_new in reindexed_data:
            if e_new['MFG_SERIAL'] == validated_entry['MFG_SERIAL']:
                return e_new
        # This part should ideally not be reached if save is successful and MFG_SERIAL is unique
        logger.error(f"Failed to find newly added entry {validated_entry['MFG_SERIAL']} in reindexed data.")
        return validated_entry # Fallback

    @staticmethod
    def update_entry(data_type: Literal['ppm', 'ocm'], mfg_serial: str, new_entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing entry. MFG_SERIAL cannot be changed.
        'NO' field is preserved. Status is recalculated.
        """
        entry_copy = new_entry_data.copy()
        entry_copy.pop('NO', None)  # 'NO' is preserved from existing, not taken from input

        if 'MFG_SERIAL' in entry_copy and entry_copy['MFG_SERIAL'] != mfg_serial:
            raise ValueError(f"Cannot change MFG_SERIAL. Attempted to change from '{mfg_serial}' to '{entry_copy['MFG_SERIAL']}'.")
        entry_copy['MFG_SERIAL'] = mfg_serial # Ensure MFG_SERIAL is part of the dict for validation

        # Recalculate status or use provided status
        if 'Status' not in entry_copy or entry_copy['Status'] is None:
            entry_copy['Status'] = DataService.calculate_status(entry_copy, data_type)

        try:
            if data_type == 'ppm':
                # Populate/update quarter dates before validation for PPM type
                installation_date_str = entry_copy.get('Installation_Date')
                q_dates = DataService._calculate_ppm_quarter_dates(installation_date_str)
                for i, q_key in enumerate(['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']):
                    # new_entry_data (aliased as entry_copy) should have PPM_Q_X fields as dicts
                    quarter_data_dict = entry_copy.get(q_key, {})
                    if not isinstance(quarter_data_dict, dict):
                        quarter_data_dict = {} # Initialize if somehow missing or wrong type
                    quarter_data_dict['quarter_date'] = q_dates[i]
                    entry_copy[q_key] = quarter_data_dict

                validated_model = PPMEntry(**entry_copy)
            else:
                validated_model = OCMEntry(**entry_copy)
            validated_entry_dict = validated_model.model_dump()
        except ValidationError as e:
            logger.error(f"Validation error updating {data_type} entry {mfg_serial}: {str(e)}")
            raise ValueError(f"Invalid {data_type.upper()} entry data for update: {e}") from e

        all_data = DataService.load_data(data_type)
        entry_found_and_updated = False

        # Ensure MFG_SERIAL uniqueness if it were allowed to change (but it's not here)
        # If MFG_SERIAL in entry_copy is different from path mfg_serial, and that new serial already exists (excluding current object)
        # This is not needed here as we forbid MFG_SERIAL change.

        updated_data_list = []
        original_no = None
        for i, existing_entry in enumerate(all_data):
            if existing_entry.get('MFG_SERIAL') == mfg_serial:
                original_no = existing_entry.get('NO') # Preserve original 'NO'
                # Update the entry, ensuring 'NO' is preserved
                entry_to_save = validated_entry_dict.copy()
                entry_to_save['NO'] = original_no
                updated_data_list.append(entry_to_save)
                entry_found_and_updated = True
            else:
                updated_data_list.append(existing_entry)

        if not entry_found_and_updated:
            raise KeyError(f"Entry with MFG_SERIAL '{mfg_serial}' not found for update.")

        # Reindexing is generally good practice after any modification that could affect order or if 'NO' needs recalculation
        # However, if 'NO' is strictly preserved and no deletions, it might be skipped.
        # For safety, reindex if there's any doubt. Here, we've preserved NO.
        # Let's assume reindex handles 'NO' correctly even if we set it.
        reindexed_data = DataService.reindex(updated_data_list)
        DataService.save_data(reindexed_data, data_type)

        # Return the updated entry from the saved data
        for e_upd in reindexed_data:
            if e_upd['MFG_SERIAL'] == mfg_serial:
                return e_upd

        logger.error(f"Failed to find updated entry {mfg_serial} in reindexed data after saving.")
        # This indicates a potential issue if not found, but validated_entry_dict is the data we attempted to save
        return validated_entry_dict # Fallback, but should be found above

    @staticmethod
    def delete_entry(data_type: Literal['ppm', 'ocm'], mfg_serial: str) -> bool:
        """Delete an entry.

        Args:
            data_type: Type of data to delete entry from ('ppm' or 'ocm')
            mfg_serial: MFG_SERIAL of entry to delete

        Returns:
            True if entry was deleted, False if not found
        """
        data = DataService.load_data(data_type)
        initial_len = len(data)
        # Filter out the entry to delete
        data[:] = [e for e in data if e.get('MFG_SERIAL') != mfg_serial]

        if len(data) == initial_len:
            return False # Entry not found

        reindexed_data = DataService.reindex(data) # Reindex after deletion
        DataService.save_data(reindexed_data, data_type)
        return True

    @staticmethod
    def get_entry(data_type: Literal['ppm', 'ocm'], mfg_serial: str) -> Optional[Dict[str, Any]]:
        """Get an entry by MFG_SERIAL.

        Args:
            data_type: Type of data to get entry from ('ppm' or 'ocm')
            mfg_serial: MFG_SERIAL of entry to get

        Returns:
            Entry if found, None otherwise
        """
        data = DataService.load_data(data_type)
        for entry in data:
            if entry.get('MFG_SERIAL') == mfg_serial:
                return entry
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
        'NO' field in CSV is ignored. MFG_SERIAL uniqueness is enforced by replacing existing.
        Status is calculated if not provided or invalid.
        Args:
            data_type: The type of data ('ppm' or 'ocm').
            file_stream: The text IO stream of the CSV file.
        Returns:
            A dictionary containing import status (added_count, updated_count, skipped_count, errors).
        """
        added_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        # Define expected columns based on models (excluding 'NO' as it's auto-generated)
        # and QuarterData objects which need special handling for PPM.
        if data_type == 'ppm':
            Model = PPMEntry
            # CSV columns should match PPMEntry fields.
            # PPM_Q_I, PPM_Q_II, PPM_Q_III, PPM_Q_IV in CSV will contain engineer names.
            expected_base_columns = [f.name for f in Model.model_fields.values() if f.name not in ['NO', 'PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']]
            quarter_eng_columns = ['PPM_Q_I_Engineer', 'PPM_Q_II_Engineer', 'PPM_Q_III_Engineer', 'PPM_Q_IV_Engineer']
            # Actual CSV columns expected for PPM
            # We expect Eng1, Eng2, Eng3, Eng4 directly as per new model.
            # The PPM_Q_X fields are QuarterData which only hold an engineer.
            # So the CSV should provide Eng1, Eng2, Eng3, Eng4 directly.
            # Let's adjust: the model has Eng1, Eng2, Eng3, Eng4, and PPM_Q_I to IV for engineers.
            # The prompt says "Eng1 (String), Eng2 (String), Eng3 (String), Eng4 (String)" for PPMEntry
            # And PPM_Q_I to IV are QuarterData (holding engineer). This is confusing.
            # Let's assume the CSV will provide Eng1, Eng2, Eng3, Eng4 AND the PPM_Q_X engineer names.
            # Re-reading the model changes: PPMEntry has Eng1, Eng2, Eng3, Eng4.
            # And PPM_Q_I, PPM_Q_II, PPM_Q_III, PPM_Q_IV are QuarterData objects.
            # QuarterData was simplified to only contain 'engineer'.
            # So, CSV should have: ... Eng1, Eng2, Eng3, Eng4, PPM_Q_I_engineer, PPM_Q_II_engineer ...
            # This is still a bit ambiguous. Let's assume the model fields Eng1-4 are primary for "who did it"
            # and PPM_Q_I to IV are for "who is scheduled for quarter X".
            # The prompt stated: "Add Eng1, Eng2, Eng3, Eng4 (String)" and "PPM_Q_I: QuarterData" (which holds engineer)
            # Let's assume the CSV will provide the fields as they are in the model,
            # with PPM_Q_I etc. being dicts like {"engineer": "name"} or just the name.
            # For simplicity of CSV, we'll expect PPM_Q_I_Engineer, etc.

            # Define expected CSV columns for PPM import
            PPM_CSV_BASE_FIELDS = ['EQUIPMENT', 'MODEL', 'Name', 'MFG_SERIAL', 'MANUFACTURER', 'Department', 'LOG_NO', 'Installation_Date', 'Warranty_End', 'Status', 'OCM']
            PPM_CSV_QUARTER_ENGINEER_FIELDS = ['Q1_Engineer', 'Q2_Engineer', 'Q3_Engineer', 'Q4_Engineer']
            PPM_EXPECTED_CSV_COLS = PPM_CSV_BASE_FIELDS + PPM_CSV_QUARTER_ENGINEER_FIELDS
            Model = PPMEntry
        else: # ocm
            Model = OCMEntry
            # For OCM, we can still derive from model fields, assuming direct mapping
            OCM_EXPECTED_CSV_COLS = [f for f in OCMEntry.model_fields if f != 'NO']


        try:
            df = pd.read_csv(file_stream, dtype=str) # Read all as string initially
            df.fillna('', inplace=True) # Replace NaN with empty strings

            if 'NO' in df.columns: # 'NO' is ignored from CSV
                df = df.drop(columns=['NO'])

            current_data_map = {entry['MFG_SERIAL']: entry for entry in DataService.load_data(data_type)}

            for index, row in df.iterrows():
                row_dict_raw = row.to_dict()
                entry_data = {}

                if data_type == 'ppm':
                    # Map base PPM fields
                    for field_name in PPM_CSV_BASE_FIELDS:
                        raw_value = row_dict_raw.get(field_name, '').strip()
                        # Handle optional fields that should be None if empty
                        if field_name in ['Name', 'Installation_Date', 'Warranty_End', 'OCM'] and not raw_value:
                            entry_data[field_name] = None
                        else:
                            entry_data[field_name] = raw_value

                    # Calculate quarter dates
                    installation_date_csv = entry_data.get('Installation_Date')
                    calculated_q_dates = DataService._calculate_ppm_quarter_dates(installation_date_csv)

                    # Populate PPM_Q_I to PPM_Q_IV
                    entry_data['PPM_Q_I'] = {
                        'engineer': row_dict_raw.get('Q1_Engineer', '').strip() or None,
                        'quarter_date': calculated_q_dates[0]
                    }
                    entry_data['PPM_Q_II'] = {
                        'engineer': row_dict_raw.get('Q2_Engineer', '').strip() or None,
                        'quarter_date': calculated_q_dates[1]
                    }
                    entry_data['PPM_Q_III'] = {
                        'engineer': row_dict_raw.get('Q3_Engineer', '').strip() or None,
                        'quarter_date': calculated_q_dates[2]
                    }
                    entry_data['PPM_Q_IV'] = {
                        'engineer': row_dict_raw.get('Q4_Engineer', '').strip() or None,
                        'quarter_date': calculated_q_dates[3]
                    }
                else: # OCM data type
                    for field_name in OCM_EXPECTED_CSV_COLS:
                        raw_value = row_dict_raw.get(field_name, '').strip()
                        # Handle optional fields for OCM if any are treated as None when empty
                        # For now, assuming OCM fields are fine with empty strings or have specific validators
                        entry_data[field_name] = raw_value

                # Optional: Name field logic (common to both, if applicable, already handled for PPM)
                if data_type == 'ocm' and 'Name' in entry_data and 'MODEL' in entry_data:
                    if not entry_data['Name'] or entry_data['Name'] == entry_data['MODEL']:
                        entry_data['Name'] = None

                # Date validation for required model date fields (PPM: none required, OCM: some might be)
                # Note: PPMEntry Installation_Date/Warranty_End are Optional[str], validator handles None/empty.
                # OCMEntry date fields might be mandatory string, needing validation here if not ''

                # For PPM, specific date fields like Installation_Date, Warranty_End are already set to None if empty.
                # Their validation (DD/MM/YYYY if not empty) happens in the PPMEntry model.
                # For OCM, let's assume similar handling or that model validators are sufficient.
                # The original code had a loop here, which is good for explicit checks if needed.
                # For now, relying on Pydantic model validation for date formats.

                # Status: Use from CSV if valid, else calculate
                # Status field is in PPM_CSV_BASE_FIELDS, so it's already in entry_data if provided.
                # If not provided or invalid, it will be calculated.
                csv_status_value = entry_data.get('Status') # Might be None if column was missing or empty and mapped to None
                if isinstance(csv_status_value, str): # Ensure it's a string before stripping
                    csv_status_value = csv_status_value.strip()

                valid_statuses = get_args(Literal["Upcoming", "Overdue", "Maintained"])
                if csv_status_value and csv_status_value in valid_statuses:
                    entry_data['Status'] = csv_status_value # Use valid provided status
                else:
                    if csv_status_value and csv_status_value not in valid_statuses: # Log if invalid status was provided
                         errors.append(f"Row {index+2}: Invalid Status '{csv_status_value}'. Will be recalculated.")
                    # Calculate status if not provided, or if provided status was invalid, or if it was None
                    entry_data['Status'] = DataService.calculate_status(entry_data, data_type)

                try:
                    validated_model = Model(**entry_data)
                    validated_dict = validated_model.model_dump()

                    mfg_serial = validated_dict['MFG_SERIAL']
                    if not mfg_serial:
                        errors.append(f"Row {index+2}: MFG_SERIAL is empty. Skipping.")
                        skipped_count +=1
                        continue

                    if mfg_serial in current_data_map:
                        # Update existing entry (preserve 'NO')
                        validated_dict['NO'] = current_data_map[mfg_serial].get('NO')
                        current_data_map[mfg_serial] = validated_dict # Replace in map
                        updated_count += 1
                    else:
                        # Add as new entry (NO will be assigned later)
                        current_data_map[mfg_serial] = validated_dict # Add to map
                        added_count += 1

                except ValidationError as e:
                    msg = f"Row {index+2} ({row_dict_raw.get('MFG_SERIAL', 'N/A')}): Validation error: {str(e)}"
                    errors.append(msg)
                    skipped_count += 1
                    continue
                except Exception as ex: # Catch any other unexpected error during processing a row
                    msg = f"Row {index+2} ({row_dict_raw.get('MFG_SERIAL', 'N/A')}): Unexpected error: {str(ex)}"
                    errors.append(msg)
                    skipped_count += 1
                    continue

            # Save all processed entries (new and updated)
            final_data_list = list(current_data_map.values())
            reindexed_data = DataService.reindex(final_data_list)
            DataService.save_data(reindexed_data, data_type)

        except pd.errors.EmptyDataError:
            errors.append("Import Error: The uploaded CSV file is empty.")
        except KeyError as e: # More specific for missing columns if not handled by get()
            errors.append(f"Import Error: Missing expected column in CSV: {e}.")
        except Exception as e:
            logger.error(f"Generic import data error: {str(e)}")
            errors.append(f"Import failed due to an unexpected error: {str(e)}")
            # If a df was loaded, count all its rows as skipped.
            skipped_count = df.shape[0] if 'df' in locals() else skipped_count + (added_count + updated_count)
            added_count = 0 # Reset counts as save might not have happened
            updated_count = 0

        return {
            "added_count": added_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "errors": errors
        }

        return {
            "added_count": added_count,
            "skipped_count": skipped_count,
            "errors": errors
        }

    @staticmethod
    def export_data(data_type: str) -> str:
        """
        Export data of the specified type to CSV format.

        Args:
            data_type: The type of data to export ('ppm' or 'ocm').

        Returns:
            The CSV content as a string.
        """
        if data_type not in ['ppm', 'ocm']:
            raise ValueError("Unsupported data type for export. Choose 'ppm' or 'ocm'.")

        all_data = DataService.load_data(data_type)
        if not all_data:
            return ""

        output = io.StringIO()
        writer = None

        if data_type == 'ppm':
            Model = PPMEntry
            # Define specific column order for PPM export
            PPM_EXPORT_COLUMNS = [
                'NO', 'EQUIPMENT', 'MODEL', 'Name', 'MFG_SERIAL', 'MANUFACTURER',
                'Department', 'LOG_NO', 'Installation_Date', 'Warranty_End', 'OCM', 'Status',
                'Q1_Date', 'Q1_Engineer', 'Q2_Date', 'Q2_Engineer',
                'Q3_Date', 'Q3_Engineer', 'Q4_Date', 'Q4_Engineer'
            ]
            writer = csv.DictWriter(output, fieldnames=PPM_EXPORT_COLUMNS, extrasaction='ignore')
            writer.writeheader()

            for entry_model_dict in all_data:
                row_to_write = {}
                # Populate base fields
                for col in PPM_EXPORT_COLUMNS:
                    if col.startswith('Q1_') or col.startswith('Q2_') or \
                       col.startswith('Q3_') or col.startswith('Q4_'):
                        continue # Skip quarter fields, will handle next
                    row_to_write[col] = entry_model_dict.get(col, '')

                # Populate flattened quarter data
                ppm_q_map = {
                    'PPM_Q_I': ('Q1_Date', 'Q1_Engineer'),
                    'PPM_Q_II': ('Q2_Date', 'Q2_Engineer'),
                    'PPM_Q_III': ('Q3_Date', 'Q3_Engineer'),
                    'PPM_Q_IV': ('Q4_Date', 'Q4_Engineer'),
                }
                for q_model_field, (q_date_col, q_eng_col) in ppm_q_map.items():
                    quarter_data = entry_model_dict.get(q_model_field, {})
                    if not isinstance(quarter_data, dict): quarter_data = {} # Ensure dict
                    row_to_write[q_date_col] = quarter_data.get('quarter_date', '')
                    row_to_write[q_eng_col] = quarter_data.get('engineer', '')

                writer.writerow(row_to_write)

        else: # ocm
            Model = OCMEntry
            # For OCM, can derive from model fields, assuming direct mapping and NO first.
            ocm_columns = ['NO'] + [field for field in Model.model_fields if field != 'NO']
            writer = csv.DictWriter(output, fieldnames=ocm_columns, extrasaction='ignore')
            writer.writeheader()

            for entry_model_dict in all_data:
                # Dates are already strings in DD/MM/YYYY in the model due to validators for OCM too
                writer.writerow(entry_model_dict)

        return output.getvalue()
