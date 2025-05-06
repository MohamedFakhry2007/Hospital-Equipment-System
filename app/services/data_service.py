"""
Data service for managing equipment maintenance data.
"""
import json
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
                return json.loads(content)
        except json.JSONDecodeError as e:
             logger.error(f"Error decoding JSON from {file_path}: {str(e)}")
             # Decide how to handle: return empty list or raise specific error
             # For robustness, let's return an empty list and log the error.
             return []
        except Exception as e:
            logger.error(f"Error loading {data_type} data: {str(e)}")
            return [] # Or raise exception


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
        except Exception as e:
            logger.error(f"Error saving {data_type} data: {str(e)}")
            raise

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
        entry_copy.pop('NO', None) # Remove 'NO' if present, it will be reassigned

        try:
            if data_type == 'ppm':
                validated_entry = PPMEntry(**entry_copy).model_dump()
            else:
                validated_entry = OCMEntry(**entry_copy).model_dump()
        except ValidationError as e:
            logger.error(f"Validation error adding entry: {str(e)}")
            raise ValueError(f"Invalid {data_type.upper()} entry data.") from e

        data = DataService.load_data(data_type)
        DataService.ensure_unique_mfg_serial(data, validated_entry) # Check uniqueness

        data.append(validated_entry)
        reindexed_data = DataService.reindex(data)
        DataService.save_data(reindexed_data, data_type)

        # Find the added entry in the reindexed list to return it with 'NO'
        for e in reindexed_data:
            if e['MFG_SERIAL'] == validated_entry['MFG_SERIAL']:
                return e
        return validated_entry # Fallback (should not happen)


    @staticmethod
    def update_entry(data_type: Literal['ppm', 'ocm'], mfg_serial: str, new_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing entry.

        Args:
            data_type: Type of data to update entry in ('ppm' or 'ocm')
            mfg_serial: MFG_SERIAL of entry to update
            new_entry: New entry data

        Returns:
            Updated entry

        Raises:
            ValueError: If entry is invalid or MFG_SERIAL is changed
            KeyError: If entry with given MFG_SERIAL does not exist
        """
        entry_copy = new_entry.copy()
        entry_copy.pop('NO', None) # Remove 'NO' field if present

        # Ensure MFG_SERIAL is not being changed
        if entry_copy.get('MFG_SERIAL') != mfg_serial:
            raise ValueError(f"Cannot update MFG_SERIAL from '{mfg_serial}' to '{entry_copy.get('MFG_SERIAL')}'")

        try:
            if data_type == 'ppm':
                validated_entry = PPMEntry(**entry_copy).model_dump()
            else:
                validated_entry = OCMEntry(**entry_copy).model_dump()
        except ValidationError as e:
            logger.error(f"Validation error updating entry: {str(e)}")
            raise ValueError(f"Invalid {data_type.upper()} entry data.") from e

        data = DataService.load_data(data_type)
        entry_found = False
        updated_data = []
        for existing_entry in data:
            if existing_entry.get('MFG_SERIAL') == mfg_serial:
                 # Preserve the 'NO' from the original entry
                validated_entry['NO'] = existing_entry.get('NO')
                updated_data.append(validated_entry)
                entry_found = True
            else:
                updated_data.append(existing_entry)

        if not entry_found:
            raise KeyError(f"Entry with MFG_SERIAL '{mfg_serial}' not found")

        # Reindexing might not be strictly necessary if NO is preserved,
        # but can ensure consistency if deletions happened previously.
        reindexed_data = DataService.reindex(updated_data)
        DataService.save_data(reindexed_data, data_type)

        # Find the updated entry in the reindexed list
        for e in reindexed_data:
            if e['MFG_SERIAL'] == mfg_serial:
                return e
        return validated_entry # Fallback


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
        Bulk import data from a CSV file stream, skipping 'NO' field in the CSV.
        Normalizes values and ensures uniqueness of MFG_SERIAL before saving.
        Args:
            data_type: The type of data ('ppm' or 'ocm').
            file_stream: The text IO stream of the CSV file.
        Returns:
            A dictionary containing import status (added_count, skipped_count, errors).
        """
        added_count = 0
        skipped_count = 0
        errors = []
        new_entries_validated = []

        try:
            df = pd.read_csv(file_stream)
            df.fillna('', inplace=True)  # Replace NaN with empty strings
            df = df.astype(str)

            if 'NO' in df.columns:
                df = df.drop(columns=['NO'])

            existing_data = DataService.load_data(data_type)

            for index, row in df.iterrows():
                row_dict = row.to_dict()
                combined_entry = {}

                # Only need Q1 date and all engineers
                q1_date = row_dict.get('PPM Q I', '').strip()
                if not q1_date:
                    msg = f"Row {index+2}: Missing Q1 date"
                    logger.warning(msg)
                    errors.append(msg)
                    skipped_count += 1
                    continue

                try:
                    other_dates = ValidationService.generate_quarter_dates(q1_date)
                except ValueError as e:
                    msg = f"Row {index+2}: Invalid Q1 date: {e}"
                    logger.warning(msg)
                    errors.append(msg)
                    skipped_count += 1
                    continue


                # Map engineers
                engineer_mapping = {
                    'I': ('Q1_ENGINEER', q1_date),
                    'II': ('Q2_ENGINEER', other_dates[0]),
                    'III': ('Q3_ENGINEER', other_dates[1]),
                    'IV': ('Q4_ENGINEER', other_dates[2])
                }

                # Set up quarter data
                for q_key, (eng_col, date_val) in engineer_mapping.items():
                    eng_val = row_dict.get(eng_col, '').strip()
                    combined_entry[f'PPM_Q_{q_key}'] = {
                        'date': date_val,
                        'engineer': eng_val or 'Not Assigned'  # Default engineer if empty
                    }

                # Map common fields
                if data_type == 'ppm':
                    required_fields = ['EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO', 'PPM']
                else:
                    required_fields = ['EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO', 'OCM', 'ENGINEER']

                missing = [f for f in required_fields if not row_dict.get(f, '').strip()]
                if missing:
                    msg = f"Skipping row {index+2}: Missing required fields: {', '.join(missing)}"
                    logger.warning(msg)
                    errors.append(msg)
                    skipped_count += 1
                    continue

                # Populate entry with normalized values
                combined_entry.update({
                    'EQUIPMENT': row_dict.get('EQUIPMENT', '').strip(),
                    'MODEL': row_dict.get('MODEL', '').strip(),
                    'MFG_SERIAL': row_dict.get('MFG_SERIAL', '').strip(),
                    'MANUFACTURER': row_dict.get('MANUFACTURER', '').strip(),
                    'LOG_NO': str(row_dict.get('LOG_NO', '')).strip(),
                    'PPM': row_dict.get('PPM', '').strip().capitalize() if 'PPM' in row_dict else '',
                    'OCM': row_dict.get('OCM', '').strip().capitalize() if 'OCM' in row_dict else '',
                    'ENGINEER': row_dict.get('ENGINEER', '').strip(),
                    'OCM_2024': row_dict.get('OCM_2024', '').strip(),
                    'OCM_2025': row_dict.get('OCM_2025', '').strip(),
                })

                # Normalize PPM value to match Literal['Yes', 'No']
                if data_type == 'ppm':
                    ppm_val = combined_entry['PPM'].lower()
                    if ppm_val in ('yes', 'no'):
                        combined_entry['PPM'] = 'Yes' if ppm_val == 'yes' else 'No'
                    else:
                        msg = f"Skipping row {index+2}: Invalid PPM value '{combined_entry['PPM']}'"
                        logger.warning(msg)
                        errors.append(msg)
                        skipped_count += 1
                        continue

                # Validate against Pydantic model
                try:
                    if data_type == 'ppm':
                        validated = PPMEntry(**combined_entry).model_dump()
                    else:
                        validated = OCMEntry(**combined_entry).model_dump()
                except ValidationError as e:
                    msg = f"Validation error on row {index+2}: {str(e)}"
                    logger.warning(msg)
                    errors.append(msg)
                    skipped_count += 1
                    continue

                # Check for duplicates and handle replacement
                mfg_serial = validated['MFG_SERIAL']
                duplicate_found = False

                # Check in existing data and replace if found
                for i, entry in enumerate(existing_data):
                    if entry['MFG_SERIAL'] == mfg_serial:
                        existing_data[i] = validated
                        duplicate_found = True
                        msg = f"Row {index+2}: Replaced existing entry with MFG_SERIAL '{mfg_serial}'"
                        logger.info(msg)
                        errors.append(msg)
                        break

                # Check in new entries and replace if found
                if not duplicate_found:
                    for i, entry in enumerate(new_entries_validated):
                        if entry['MFG_SERIAL'] == mfg_serial:
                            new_entries_validated[i] = validated
                            duplicate_found = True
                            msg = f"Row {index+2}: Replaced previously imported entry with MFG_SERIAL '{mfg_serial}'"
                            logger.info(msg)
                            errors.append(msg)
                            break

                # If no duplicate found, add as new entry
                if not duplicate_found:
                    new_entries_validated.append(validated)
                    added_count += 1

            # Save valid entries after processing all rows
            if new_entries_validated:
                updated_data = existing_data + new_entries_validated
                reindexed_data = DataService.reindex(updated_data)
                DataService.save_data(reindexed_data, data_type)

        except pd.errors.EmptyDataError:
            msg = "Import Error: The uploaded CSV file is empty."
            logger.error(msg)
            errors.append(msg)
            skipped_count = len(df.index) if 'df' in locals() else 0
        except KeyError as e:
            msg = f"Import Error: Missing expected column in CSV: {e}. Please check the header."
            logger.error(msg)
            errors.append(msg)
        except Exception as e:
            msg = f"Import failed: An unexpected error occurred - {str(e)}"
            logger.exception(msg)
            errors.append(msg)
            skipped_count = df.shape[0] if 'df' in locals() else 0

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
            data_type: The type of data to export ('ppm').

        Returns:
            The CSV content as a string.

        Raises:
            ValueError: If the data type is not supported.
        """
        if data_type != 'ppm':
            raise ValueError("Unsupported data type for export. Only 'ppm' is supported.")

        data = DataService.load_data(data_type)

        # Flatten and transform data
        flat_data = []
        for entry in data:
            flat_entry = {
                'NO': entry.get('NO'),
                'EQUIPMENT': entry.get('EQUIPMENT'),
                'MODEL': entry.get('MODEL'),
                'MFG_SERIAL': entry.get('MFG_SERIAL'),
                'MANUFACTURER': entry.get('MANUFACTURER'),
                'LOG_NO': entry.get('LOG_NO'),
                'PPM': entry.get('PPM'),
                'OCM': entry.get('OCM', '')
            }
            for roman, num, q_key in [('I', 1, 'PPM_Q_I'), ('II', 2, 'PPM_Q_II'), ('III', 3, 'PPM_Q_III'), ('IV', 4, 'PPM_Q_IV')]:
                q_data = entry.get(q_key, {})
                flat_entry[f'PPM Q {roman}'] = q_data.get('date', '')
                flat_entry[f'Q{num}_ENGINEER'] = q_data.get('engineer', '')
            flat_data.append(flat_entry)

        # Define CSV columns order
        columns_order = ['NO', 'EQUIPMENT', 'MODEL', 'MFG_SERIAL', 'MANUFACTURER', 'LOG_NO', 'PPM', 'OCM',
                       'PPM Q I', 'Q1_ENGINEER', 'PPM Q II', 'Q2_ENGINEER', 'PPM Q III', 'Q3_ENGINEER', 'PPM Q IV', 'Q4_ENGINEER']

        # Generate CSV content using csv library
        with io.StringIO() as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns_order)
            writer.writeheader()
            writer.writerows(flat_data)
            return csvfile.getvalue()

class ValidationService:
    @staticmethod
    def generate_quarter_dates(q1_date_str: str) -> List[str]:
        """Generates Q2, Q3, Q4 dates based on Q1 date.

        Args:
            q1_date_str: Q1 date string (YYYY-MM-DD).

        Returns:
            A list of Q2, Q3, Q4 date strings.

        Raises:
            ValueError: if the input date is invalid.
        """
        try:
            q1_date = datetime.strptime(q1_date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid Q1 date format. Use YYYY-MM-DD.")

        q2_date = q1_date + timedelta(days=90)
        q3_date = q2_date + timedelta(days=90)
        q4_date = q3_date + timedelta(days=90)

        return [q2_date.strftime('%Y-%m-%d'), q3_date.strftime('%Y-%m-%d'), q4_date.strftime('%Y-%m-%d')]