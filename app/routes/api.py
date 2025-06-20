"""API routes for managing equipment maintenance data."""
import logging
from pathlib import Path

import io # Added for TextIOWrapper
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request, Response, current_app # send_file might not be needed now
from datetime import datetime

from app.services.data_service import DataService
# training_service is imported directly in the route functions now
# from app.services.training_service import TrainingService
from app.config import Config # Added for VAPID public key
from app.services import training_service # Import the module

# ImportExportService and ValidationService removed

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        logger.addHandler(handler)

@api_bp.route('/equipment/<data_type>', methods=['GET'])
def get_equipment(data_type):
    """Get all equipment entries."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    try:
        entries = DataService.get_all_entries(data_type)
        return jsonify(entries), 200
    except Exception as e:
        logger.error(f"Error getting {data_type} entries: {str(e)}")
        return jsonify({"error": "Failed to retrieve equipment data"}), 500

@api_bp.route('/equipment/<data_type>/<SERIAL>', methods=['GET'])
def get_equipment_by_serial(data_type, SERIAL):
    """Get a specific equipment entry by SERIAL."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    try:
        entry = DataService.get_entry(data_type, SERIAL)
        if entry:
            return jsonify(entry), 200
        else:
            return jsonify({"error": f"Equipment with serial '{SERIAL}' not found"}), 404
    except Exception as e:
        logger.error(f"Error getting {data_type} entry {SERIAL}: {str(e)}")
        return jsonify({"error": "Failed to retrieve equipment data"}), 500

@api_bp.route('/equipment/<data_type>', methods=['POST'])
def add_equipment(data_type):
    """Add a new equipment entry."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Basic validation (more thorough validation in service layer)
    # if 'SERIAL' not in data: # This will be caught by DataService Pydantic validation
    #      return jsonify({"error": "SERIAL is required"}), 400

    try:
        # Data is passed directly; Pydantic validation happens in DataService.add_entry
        added_entry = DataService.add_entry(data_type, data)
        return jsonify(added_entry), 201
    except ValueError as e:
        logger.warning(f"Validation error adding {data_type} entry: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error adding {data_type} entry: {str(e)}")
        return jsonify({"error": "Failed to add equipment"}), 500


@api_bp.route('/equipment/<data_type>/<SERIAL>', methods=['PUT'])
def update_equipment(data_type, SERIAL):
    """Update an existing equipment entry."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Ensure SERIAL in payload matches the URL parameter
    if data.get('SERIAL') != SERIAL:
         return jsonify({"error": "SERIAL in payload must match URL parameter"}), 400

    try:
        # Convert JSON data if needed before validation/update
        updated_entry = DataService.update_entry(data_type, SERIAL, data)
        return jsonify(updated_entry), 200
    except ValueError as e:
        logger.warning(f"Validation error updating {data_type} entry {SERIAL}: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except KeyError:
         return jsonify({"error": f"Equipment with serial '{SERIAL}' not found"}), 404
    except Exception as e:
        logger.error(f"Error updating {data_type} entry {SERIAL}: {str(e)}")
        return jsonify({"error": "Failed to update equipment"}), 500


@api_bp.route('/equipment/<data_type>/<SERIAL>', methods=['DELETE'])
def delete_equipment(data_type, SERIAL):
    """Delete an equipment entry."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    try:
        deleted = DataService.delete_entry(data_type, SERIAL)
        if deleted:
            return jsonify({"message": f"Equipment with serial '{SERIAL}' deleted successfully"}), 200
        else:
            return jsonify({"error": f"Equipment with serial '{SERIAL}' not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting {data_type} entry {SERIAL}: {str(e)}")
        return jsonify({"error": "Failed to delete equipment"}), 500


@api_bp.route('/export/<data_type>', methods=['GET'])
def export_data(data_type):
    """Export data to CSV."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    try:
        csv_content = DataService.export_data(data_type)
        if csv_content is None or csv_content == "": # Handle empty data case from service
            # Optionally return 204 No Content, or an empty CSV with headers
            # Current DataService.export_data returns "" if no data.
            # For consistency, we can make it return headers only.
            # For now, if it's empty string, send it as such.
            pass

        filename = f"{data_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition":
                        f"attachment; filename={filename}"})
    except Exception as e:
        logger.error(f"Error exporting {data_type} data: {str(e)}")
        return jsonify({"error": f"Failed to export {data_type} data"}), 500


@api_bp.route('/import/<data_type>', methods=['POST'])
def import_data(data_type):
    """Import data from CSV."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith('.csv'):
        try:
            # Wrap the file stream for text-mode processing
            # file.stream is a SpooledTemporaryFile, which is binary.
            # TextIOWrapper makes it behave like a text file.
            file_stream = io.TextIOWrapper(file.stream, encoding='utf-8')

            # Call DataService.import_data directly with the stream
            import_results = DataService.import_data(data_type, file_stream)

            # Check for errors in import_results to determine status code
            if import_results.get("errors") and (import_results.get("added_count", 0) == 0 and import_results.get("updated_count", 0) == 0) :
                # If there are errors and nothing was added or updated, consider it a failure.
                # Or if only skipped_count > 0 and errors exist.
                status_code = 400 # Bad request if all rows failed or file was problematic
            elif import_results.get("errors"):
                status_code = 207 # Multi-Status if some rows succeeded and some failed
            else:
                status_code = 200 # OK if all succeeded

            return jsonify(import_results), status_code

        except Exception as e:
            logger.error(f"Error importing {data_type} data: {str(e)}")
            return jsonify({"error": f"Failed to import {data_type} data: {str(e)}", "details": str(e)}), 500
    else:
        return jsonify({"error": "Invalid file type, only CSV allowed"}), 400

@api_bp.route('/bulk_delete/<data_type>', methods=['POST'])
def bulk_delete(data_type):
    """Handle bulk deletion of equipment entries."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({'success': False, 'message': 'Invalid data type'}), 400

    serials = request.json.get('serials', [])
    if not serials:
        return jsonify({'success': False, 'message': 'No serials provided'}), 400

    deleted_count = 0
    not_found = 0

    for serial in serials:
        if DataService.delete_entry(data_type, serial):
            deleted_count += 1
        else:
            not_found += 1

    return jsonify({
        'success': True,
        'deleted_count': deleted_count,
        'not_found': not_found
    })



# Training Records API Routes

@api_bp.route('/trainings', methods=['POST'])
def add_training_route():
    if not request.is_json:
        logger.warning("Add training request is not JSON")
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    logger.info(f"Received data for new training: {data}")
    try:
        new_record = training_service.add_training(data)
        logger.info(f"Successfully added new training record with ID: {new_record.id}")
        return jsonify(new_record.to_dict()), 201
    except ValueError as e:
        logger.warning(f"Validation error adding training: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error adding training record: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to add training record"}), 500

@api_bp.route('/trainings', methods=['GET'])
def get_all_trainings_route():
    try:
        records = training_service.get_all_trainings()
        return jsonify([record.to_dict() for record in records]), 200
    except Exception as e:
        logger.error(f"Error getting all training records: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to retrieve training records"}), 500

@api_bp.route('/trainings/<int:training_id>', methods=['GET'])
def get_training_by_id_route(training_id):
    try:
        record = training_service.get_training_by_id(training_id)
        if record:
            return jsonify(record.to_dict()), 200
        else:
            logger.warning(f"Training record with ID {training_id} not found.")
            return jsonify({"error": "Training record not found"}), 404
    except Exception as e:
        logger.error(f"Error getting training record {training_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to retrieve training record"}), 500

@api_bp.route('/trainings/<int:training_id>', methods=['PUT'])
def update_training_route(training_id):
    if not request.is_json:
        logger.warning(f"Update training request for ID {training_id} is not JSON")
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    logger.info(f"Received data for updating training ID {training_id}: {data}")
    try:
        # The service function expects training_id as a separate argument
        updated_record = training_service.update_training(training_id, data)
        if updated_record:
            logger.info(f"Successfully updated training record with ID: {training_id}")
            return jsonify(updated_record.to_dict()), 200
        else:
            logger.warning(f"Training record with ID {training_id} not found for update.")
            return jsonify({"error": "Training record not found"}), 404
    except ValueError as e:
        logger.warning(f"Validation error updating training {training_id}: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating training record {training_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to update training record"}), 500

@api_bp.route('/trainings/<int:training_id>', methods=['DELETE'])
def delete_training_route(training_id):
    try:
        success = training_service.delete_training(training_id)
        if success:
            logger.info(f"Successfully deleted training record with ID: {training_id}")
            return jsonify({"message": "Training record deleted successfully"}), 200 # 204 No Content is also common
        else:
            logger.warning(f"Training record with ID {training_id} not found for deletion.")
            return jsonify({"error": "Training record not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting training record {training_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to delete training record"}), 500

# --- Application Settings API Routes ---

@api_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get current application settings."""
    try:
        settings = DataService.load_settings()
        return jsonify(settings), 200
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        return jsonify({"error": "Failed to load settings"}), 500

@api_bp.route('/settings', methods=['POST'])
def save_settings():
    """Save application settings."""
    # Added detailed logging for headers and raw body
    logger.info(f"save_settings called. Request Method: {request.method}")
    logger.info(f"Request Headers: {request.headers}")
    logger.info(f"Request Content-Type: {request.content_type}")
    logger.info(f"Request is_json: {request.is_json}")
    logger.debug(f"Request raw data: {request.get_data(as_text=True)}") # Log raw data

    # Try to parse JSON irrespective of Content-Type header, handle failure gracefully
    data = request.get_json(force=True, silent=True)

    if data is None:
        logger.warning(f"Failed to parse request body as JSON. Request data (first 200 chars): {request.data[:200]}...")
        # The frontend reported "Invalid request format. Expected JSON."
        # We'll return a similar error, but make it clear it's from our explicit check.
        return jsonify({"error": "Invalid request format. Expected JSON data."}), 400

    logger.info(f"Successfully parsed settings data: {data}")

    # Basic validation for expected keys and types
    email_notifications_enabled = data.get("email_notifications_enabled")
    email_reminder_interval_minutes = data.get("email_reminder_interval_minutes")
    recipient_email = data.get("recipient_email", "") # Default to empty string if not provided

    push_notifications_enabled = data.get("push_notifications_enabled")
    push_notification_interval_minutes = data.get("push_notification_interval_minutes")

    if not isinstance(email_notifications_enabled, bool):
        return jsonify({"error": "Invalid type for email_notifications_enabled, boolean expected."}), 400
    if not isinstance(email_reminder_interval_minutes, int) or email_reminder_interval_minutes <= 0:
        err_msg = "Invalid value for email_reminder_interval_minutes, positive integer expected."
        return jsonify({"error": err_msg}), 400
    if not isinstance(recipient_email, str):
        return jsonify({"error": "Invalid type for recipient_email, string expected."}), 400

    if not isinstance(push_notifications_enabled, bool):
        return jsonify({"error": "Invalid type for push_notifications_enabled, boolean expected."}), 400
    if not isinstance(push_notification_interval_minutes, int) or push_notification_interval_minutes <= 0:
        err_msg = "Invalid value for push_notification_interval_minutes, positive integer expected."
        return jsonify({"error": err_msg}), 400

    # Construct settings object to save all known settings
    # It's important that DataService.save_settings either overwrites the entire file
    # or can merge settings. Assuming it overwrites with settings_to_save.
    settings_to_save = {
        "email_notifications_enabled": email_notifications_enabled,
        "email_reminder_interval_minutes": email_reminder_interval_minutes,
        "recipient_email": recipient_email.strip(),
        "push_notifications_enabled": push_notifications_enabled,
        "push_notification_interval_minutes": push_notification_interval_minutes,
    }

    # Preserve any other settings that might be in data/settings.json but not managed through this API call
    # This requires loading current settings first.
    try:
        current_settings = DataService.load_settings()
        # Update current_settings with validated values from the request
        current_settings.update(settings_to_save)
        # Now save the merged settings
        DataService.save_settings(current_settings)
        logger.info(f"Settings saved successfully: {current_settings}")
        return jsonify({"message": "Settings saved successfully", "settings": current_settings}), 200
    except ValueError as e: # Catch specific error from save_settings for IO issues
        logger.error(f"Error saving settings (ValueError): {str(e)}")
        return jsonify({"error": f"Failed to save settings: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error saving settings: {str(e)}")
        return jsonify({"error": "Failed to save settings due to an unexpected error"}), 500

@api_bp.route('/health')
def health_check():
    return 'OK', 200

# --- Push Notification API Routes ---

@api_bp.route('/vapid_public_key', methods=['GET'])
def vapid_public_key():
    """Provide the VAPID public key to the client."""
    if not Config.VAPID_PUBLIC_KEY:
        logger.error("VAPID_PUBLIC_KEY not configured on the server.")
        return jsonify({"error": "VAPID public key not configured."}), 500
    return jsonify({"publicKey": Config.VAPID_PUBLIC_KEY}), 200

@api_bp.route('/push_subscribe', methods=['POST'])
def push_subscribe():
    """
    Subscribes a client for push notifications.
    Expects a JSON payload with the PushSubscription object.
    Example: {"endpoint": "...", "keys": {"p256dh": "...", "auth": "..."}}
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    subscription_info = request.get_json()
    if not subscription_info or not subscription_info.get("endpoint"):
        return jsonify({"error": "Invalid subscription object. 'endpoint' is required."}), 400

    # Basic validation of the subscription object structure (more can be added)
    if not isinstance(subscription_info.get("keys"), dict) or \
       not subscription_info["keys"].get("p256dh") or \
       not subscription_info["keys"].get("auth"):
        return jsonify({"error": "Invalid subscription object structure. 'keys.p256dh' and 'keys.auth' are required."}), 400

    try:
        DataService.add_push_subscription(subscription_info)
        logger.info(f"Successfully subscribed for push notifications: {subscription_info.get('endpoint')[:50]}...")
        return jsonify({"message": "Subscription successful"}), 201
    except Exception as e:
        logger.error(f"Error subscribing for push notifications: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to subscribe for push notifications"}), 500

@api_bp.route('/push_unsubscribe', methods=['POST'])
def push_unsubscribe():
    """
    Unsubscribes a client from push notifications.
    Expects a JSON payload with the endpoint to unsubscribe.
    Example: {"endpoint": "..."}
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    endpoint_to_remove = data.get("endpoint")

    if not endpoint_to_remove:
        return jsonify({"error": "Invalid request. 'endpoint' is required."}), 400

    try:
        DataService.remove_push_subscription(endpoint_to_remove)
        logger.info(f"Successfully unsubscribed from push notifications: {endpoint_to_remove[:50]}...")
        return jsonify({"message": "Unsubscription successful"}), 200
    except Exception as e:
        logger.error(f"Error unsubscribing from push notifications: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to unsubscribe from push notifications"}), 500
