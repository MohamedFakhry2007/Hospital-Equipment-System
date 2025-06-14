
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Literal

# Assuming app.config exists and has DATA_DIR
# If not, this will need adjustment or Config will need to be created.
# For the subtask, we'll proceed assuming it's available.
try:
    from app.config import Config
except ImportError:
    # Fallback if app.config is not found, create a dummy Config for the script to run
    class Config:
        DATA_DIR = Path(".") / "data" # Default to a local data directory
    print("Warning: app.config.Config not found. Using a dummy Config with DATA_DIR='./data'")


# TrainingRecord model from app.models.training is not directly used for ORM operations here,
# but its structure (fields like employee_id, name, etc.) is the basis for the dicts handled.

logger = logging.getLogger(__name__)
# Ensure logger is configured if running standalone or in a context where it's not already set up
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO) # Basic config for the logger

TRAINING_DATA_PATH = Path(Config.DATA_DIR) / "training.json"

class TrainingService:
    def __init__(self):
        # No db_session needed
        self._ensure_data_file_exists()

    def _ensure_data_file_exists(self):
        data_dir = Path(Config.DATA_DIR)
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating data directory {data_dir}: {e}")
            # Depending on requirements, might re-raise or handle gracefully
            raise

        if not TRAINING_DATA_PATH.exists():
            try:
                with open(TRAINING_DATA_PATH, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            except IOError as e:
                logger.error(f"Error creating initial training data file {TRAINING_DATA_PATH}: {e}")
                raise # Re-raise as this is critical for service initialization

    def _load_data(self) -> List[Dict[str, Any]]:
        if not TRAINING_DATA_PATH.exists(): # Handle case where file might be deleted after init
            logger.warning(f"Training data file {TRAINING_DATA_PATH} not found at load time. Returning empty list.")
            return []
        try:
            with open(TRAINING_DATA_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip(): # Check if content is empty or just whitespace
                    return []
                # TODO: Add validation against a Pydantic model representing TrainingRecord structure if desired
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {TRAINING_DATA_PATH}: {e}. Returning empty list.")
            return []
        except FileNotFoundError: # Should be caught by TRAINING_DATA_PATH.exists() check earlier
            logger.warning(f"Training data file {TRAINING_DATA_PATH} not found. Returning empty list.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading training data: {e}. Returning empty list.")
            return []

    def _save_data(self, data: List[Dict[str, Any]]):
        try:
            with open(TRAINING_DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"IOError saving training data to {TRAINING_DATA_PATH}: {e}")
            raise ValueError(f"Failed to save training data due to IO error.") from e
        except Exception as e:
            logger.error(f"Unexpected error saving training data: {e}")
            raise ValueError(f"Failed to save training data due to an unexpected error.") from e

    def _generate_next_id(self, data: List[Dict[str, Any]]) -> int:
        if not data:
            return 1
        # Ensure IDs are integers and handle potential non-integer or missing IDs gracefully
        max_id = 0
        for item in data:
            item_id = item.get("id")
            if isinstance(item_id, int) and item_id > max_id:
                max_id = item_id
        return max_id + 1


    def create_training_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ["employee_id", "name"]
        for field in required_fields:
            if field not in record_data or not record_data[field]: # Checks for presence and non-emptiness
                raise ValueError(f"Missing or empty required field: {field}")

        if "trained_machines" in record_data and record_data["trained_machines"] is not None and not isinstance(record_data["trained_machines"], list):
            raise ValueError("Field 'trained_machines' must be a list or null.")

        all_records = self._load_data()

        new_id = self._generate_next_id(all_records)
        new_record = {
            "id": new_id,
            "employee_id": str(record_data["employee_id"]), # Ensure string
            "name": str(record_data["name"]),             # Ensure string
            "department": str(record_data.get("department")) if record_data.get("department") is not None else None,
            "trainer": str(record_data.get("trainer")) if record_data.get("trainer") is not None else None,
            "trained_machines": record_data.get("trained_machines", []) # Defaults to empty list if not provided
        }

        all_records.append(new_record)
        self._save_data(all_records)
        return new_record

    def get_training_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        if not isinstance(record_id, int):
            logger.warning(f"get_training_record called with non-integer ID type: {type(record_id)}.")
            return None
        all_records = self._load_data()
        for record in all_records:
            if record.get("id") == record_id:
                return record
        return None

    def get_all_training_records(self, skip: int = 0, limit: int = 0) -> List[Dict[str, Any]]:
        if not isinstance(skip, int) or skip < 0:
            logger.warning(f"Invalid skip value {skip}, defaulting to 0.")
            skip = 0
        if not isinstance(limit, int) or limit < 0:
            logger.warning(f"Invalid limit value {limit}, defaulting to 0 (no limit).")
            limit = 0

        records = self._load_data()

        start_index = skip
        if start_index >= len(records) and skip > 0 :
             return []

        end_index = len(records)
        if limit > 0:
            end_index = skip + limit
            if end_index > len(records):
                end_index = len(records)

        return records[start_index:end_index]


    def update_training_record(self, record_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(record_id, int):
            logger.warning(f"update_training_record called with non-integer ID type: {type(record_id)}.")
            return None

        all_records = self._load_data()
        record_found = False
        updated_record_instance = None

        if "id" in update_data and update_data["id"] != record_id:
            raise ValueError("Cannot change record ID during update.")

        for i, record in enumerate(all_records):
            if record.get("id") == record_id:
                current_record = all_records[i]

                for key, value in update_data.items():
                    if key == "id":
                        continue
                    if key in current_record: # Only update existing keys
                        if key == "trained_machines" and value is not None and not isinstance(value, list):
                            raise ValueError("Field 'trained_machines' must be a list or null.")
                        current_record[key] = value

                required_fields = ["employee_id", "name"]
                for field in required_fields:
                    if field in update_data and (current_record[field] is None or str(current_record[field]).strip() == ""):
                        raise ValueError(f"Required field '{field}' cannot be updated to be empty.")

                updated_record_instance = current_record
                record_found = True
                break

        if record_found:
            self._save_data(all_records)
            return updated_record_instance
        return None

    def delete_training_record(self, record_id: int) -> bool:
        if not isinstance(record_id, int):
            logger.warning(f"delete_training_record called with non-integer ID type: {type(record_id)}.")
            return False

        all_records = self._load_data()
        initial_len = len(all_records)

        all_records[:] = [record for record in all_records if record.get("id") != record_id]

        if len(all_records) < initial_len:
            self._save_data(all_records)
            return True
        return False

    def import_training_data(self, file_path: str):
        logger.warning("Import training data functionality is not yet implemented.")
        pass

    def export_training_data(self, file_format: Literal['csv', 'json'] = 'csv') -> str:
        logger.info(f"Exporting training data to {file_format}")
        all_records = self._load_data()

        if not all_records:
            return "[]" if file_format == 'json' else ""

        if file_format == 'json':
            return json.dumps(all_records, indent=2)

        elif file_format == 'csv':
            headers = ["id", "employee_id", "name", "department", "trainer", "trained_machines"]
            if all_records:
                unique_keys = set()
                for record in all_records:
                    if isinstance(record, dict):
                        unique_keys.update(record.keys())

                standard_headers_present = [h for h in headers if h in unique_keys]
                dynamic_keys = sorted(list(unique_keys - set(standard_headers_present)))
                final_headers = standard_headers_present + dynamic_keys
                if not final_headers :
                    final_headers = headers
            else:
                return ""

            import csv
            import io
            try:
                string_io = io.StringIO()
                writer = csv.DictWriter(string_io, fieldnames=final_headers, extrasaction='ignore', restval='')
                writer.writeheader()
                for record in all_records:
                    if not isinstance(record, dict):
                        logger.warning(f"Skipping non-dictionary record during CSV export: {record}")
                        continue

                    csv_record = record.copy()
                    if 'trained_machines' in csv_record and isinstance(csv_record['trained_machines'], list):
                        csv_record['trained_machines'] = ";".join(map(str, csv_record['trained_machines']))
                    writer.writerow(csv_record)
                return string_io.getvalue()
            except Exception as e:
                logger.error(f"Error writing training data to CSV string: {e}")
                return ""
        else:
            logger.warning(f"Unsupported export format: {file_format}")
            raise ValueError(f"Unsupported export format: {file_format}. Must be 'csv' or 'json'.")
