"""
Data service for managing equipment maintenance data.
"""
import json
from dateutil.relativedelta import relativedelta
import logging
import io
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, Union, TextIO
from datetime import datetime, timedelta

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
            # This logic might need refinement based on actual operational meaning of Eng1-4.

            # Simplified: If all Eng fields have values, assume "Maintained".
            # This doesn't account for "Overdue" or "Upcoming" well without explicit quarter dates.
            # For now, if any Eng field is empty, it's "Upcoming". If filled, "Maintained".
            # This is a placeholder and likely needs to be more sophisticated.
            all_eng_filled = all(entry_data.get(f"Eng{i}") for i in range(1, 5))
            if all_eng_filled:
                return "Maintained"

            # Placeholder: This doesn't distinguish Overdue from Upcoming well for PPM without dates.
            # If Installation_Date is available and very old, and not all Eng are filled, it could be Overdue.
            # For now, default to "Upcoming" if not all Eng fields are filled.
            return "Upcoming" # Needs better logic for PPM "Overdue"

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
                # For PPM, PPMEntryCreate is not defined in the problem, assume PPMEntry is used for creation
                validated_entry_model = PPMEntry(**entry_copy)
            else:
                # For OCM, OCMEntryCreate is not defined in the problem, assume OCMEntry is used for creation
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

            # Simpler approach: CSV columns match the flat field names of the Pydantic models.
            # For PPM_Q_I, it will be a dictionary in the model, so CSV needs to map to that.
            # Let's assume CSV has PPM_Q_I_engineer, PPM_Q_II_engineer, etc.
            csv_columns = list(PPMEntry.model_fields.keys())
            # We need to adjust for QuarterData fields.
            # The export will produce flat PPM_Q_I (engineer name), etc. So import should expect that.

        else: # ocm
            Model = OCMEntry
            csv_columns = list(OCMEntry.model_fields.keys())

        try:
            df = pd.read_csv(file_stream, dtype=str) # Read all as string initially
            df.fillna('', inplace=True)

            if 'NO' in df.columns: # 'NO' is ignored from CSV
                df = df.drop(columns=['NO'])

            current_data_map = {entry['MFG_SERIAL']: entry for entry in DataService.load_data(data_type)}
            entries_to_save = [] # list of dicts

            for index, row in df.iterrows():
                row_dict_raw = row.to_dict()
                entry_data = {}

                # Prepare entry_data from row_dict_raw, mapping to model fields
                for field_name in csv_columns:
                    if field_name == 'NO': continue # NO is handled by reindex

                    # Handle PPM QuarterData: CSV has PPM_Q_I, PPM_Q_II, etc. for engineer names
                    if data_type == 'ppm' and field_name in ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']:
                        # CSV header for these should be PPM_Q_I, PPM_Q_II, etc.
                        # And the value is the engineer's name for that quarter.
                        engineer_name = row_dict_raw.get(field_name, '').strip()
                        entry_data[field_name] = {"engineer": engineer_name}
                        continue

                    entry_data[field_name] = row_dict_raw.get(field_name, '').strip()

                # Optional: Name field logic (skip if same as MODEL)
                if 'Name' in entry_data and 'MODEL' in entry_data:
                    if not entry_data['Name'] or entry_data['Name'] == entry_data['MODEL']:
                        entry_data['Name'] = None # Will be skipped by Pydantic if None and Optional

                # Date validation and formatting (DD/MM/YYYY)
                date_fields = ["Installation_Date", "Warranty_End"]
                if data_type == 'ocm':
                    date_fields.extend(["Service_Date", "Next_Maintenance"])

                valid_dates = True
                for date_field in date_fields:
                    if date_field in entry_data and entry_data[date_field]:
                        try:
                            datetime.strptime(entry_data[date_field], '%d/%m/%Y')
                        except ValueError:
                            msg = f"Row {index+2}: Invalid date format for {date_field} ('{entry_data[date_field]}'). Expected DD/MM/YYYY."
                            errors.append(msg)
                            skipped_count += 1
                            valid_dates = False
                            break
                if not valid_dates:
                    continue

                # Status: Use from CSV if valid, else calculate
                csv_status = entry_data.get('Status', '').strip()
                valid_statuses = get_args(Literal["Upcoming", "Overdue", "Maintained"]) # Helper to get Literal values
                if csv_status and csv_status in valid_statuses:
                    entry_data['Status'] = csv_status
                else:
                    if csv_status and csv_status not in valid_statuses:
                         errors.append(f"Row {index+2}: Invalid Status '{csv_status}'. Will be recalculated.")
                    entry_data['Status'] = DataService.calculate_status(entry_data, data_type)


                try:
                    # Validate the prepared entry_data
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

        Model = PPMEntry if data_type == 'ppm' else OCMEntry
        # Define column order based on model fields, ensuring 'NO' is first.
        # And PPM QuarterData fields are output as flat engineer names.
        columns = ['NO'] + [field for field in Model.model_fields if field != 'NO']

        output = io.StringIO()
        # Use extrasaction='ignore' if model has fields not intended for CSV or vice-versa
        # Use extrasaction='raise' during development to catch discrepancies
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()

        for entry_model_dict in all_data:
            # Prepare row for CSV
            row_to_write = entry_model_dict.copy()

            if data_type == 'ppm':
                # Flatten PPM QuarterData fields for CSV export
                for q_field in ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']:
                    quarter_data = row_to_write.get(q_field)
                    if isinstance(quarter_data, dict):
                        row_to_write[q_field] = quarter_data.get('engineer', '')
                    elif quarter_data is not None: # Should be dict or None
                         logger.warning(f"Unexpected data type for {q_field} in entry {row_to_write.get('MFG_SERIAL')}: {type(quarter_data)}")
                         row_to_write[q_field] = '' # Default to empty if unexpected type

            # Dates are already strings in DD/MM/YYYY in the model due to validators
            writer.writerow(row_to_write)

        return output.getvalue()

# Need to import get_args for Literal introspection if used in import_data
from typing import get_args