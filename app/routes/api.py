# app/routes/api.py

"""
API routes for managing equipment maintenance data.
"""
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file, Response, current_app
from datetime import datetime

from app.services.data_service import DataService
from app.services.import_export import ImportExportService
from app.services.validation import ValidationService

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

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

@api_bp.route('/equipment/<data_type>/<mfg_serial>', methods=['GET'])
def get_equipment_by_serial(data_type, mfg_serial):
    """Get a specific equipment entry by MFG_SERIAL."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    try:
        entry = DataService.get_entry(data_type, mfg_serial)
        if entry:
            return jsonify(entry), 200
        else:
            return jsonify({"error": f"Equipment with serial '{mfg_serial}' not found"}), 404
    except Exception as e:
        logger.error(f"Error getting {data_type} entry {mfg_serial}: {str(e)}")
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
    if 'MFG_SERIAL' not in data:
         return jsonify({"error": "MFG_SERIAL is required"}), 400

    try:
        # Use validation service for form-like structure if needed,
        # but here we expect JSON matching the model structure
        # Convert JSON data to the format expected by DataService if necessary
        if data_type == 'ppm':
            # Example: Convert nested dicts if needed
             pass # Assuming JSON matches PPMEntryCreate structure
        else: # ocm
             pass # Assuming JSON matches OCMEntryCreate structure

        added_entry = DataService.add_entry(data_type, data)
        return jsonify(added_entry), 201
    except ValueError as e:
        logger.warning(f"Validation error adding {data_type} entry: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error adding {data_type} entry: {str(e)}")
        return jsonify({"error": "Failed to add equipment"}), 500


@api_bp.route('/equipment/<data_type>/<mfg_serial>', methods=['PUT'])
def update_equipment(data_type, mfg_serial):
    """Update an existing equipment entry."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Ensure MFG_SERIAL in payload matches the URL parameter
    if data.get('MFG_SERIAL') != mfg_serial:
         return jsonify({"error": "MFG_SERIAL in payload must match URL parameter"}), 400

    try:
        # Convert JSON data if needed before validation/update
        updated_entry = DataService.update_entry(data_type, mfg_serial, data)
        return jsonify(updated_entry), 200
    except ValueError as e:
        logger.warning(f"Validation error updating {data_type} entry {mfg_serial}: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except KeyError:
         return jsonify({"error": f"Equipment with serial '{mfg_serial}' not found"}), 404
    except Exception as e:
        logger.error(f"Error updating {data_type} entry {mfg_serial}: {str(e)}")
        return jsonify({"error": "Failed to update equipment"}), 500


@api_bp.route('/equipment/<data_type>/<mfg_serial>', methods=['DELETE'])
def delete_equipment(data_type, mfg_serial):
    """Delete an equipment entry."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    try:
        deleted = DataService.delete_entry(data_type, mfg_serial)
        if deleted:
            return jsonify({"message": f"Equipment with serial '{mfg_serial}' deleted successfully"}), 200
        else:
            return jsonify({"error": f"Equipment with serial '{mfg_serial}' not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting {data_type} entry {mfg_serial}: {str(e)}")
        return jsonify({"error": "Failed to delete equipment"}), 500


@api_bp.route('/export/<data_type>', methods=['GET'])
def export_data(data_type):
    """Export data to CSV."""
    if data_type not in ('ppm', 'ocm'):
        return jsonify({"error": "Invalid data type"}), 400

    try:
        success, message, csv_content = ImportExportService.export_to_csv(data_type)
        if success:
            # Create a temporary file or send content directly
            filename = f"{data_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return Response(
                csv_content,
                mimetype="text/csv",
                headers={"Content-disposition":
                         f"attachment; filename={filename}"})
        else:
            return jsonify({"error": message}), 500
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
            # Save temporary file
            upload_folder = Path(current_app.config['UPLOAD_FOLDER']) # Define UPLOAD_FOLDER in Config
            upload_folder.mkdir(exist_ok=True)
            temp_path = upload_folder / file.filename
            file.save(temp_path)

            success, message, stats = ImportExportService.import_from_csv(data_type, str(temp_path))

            # Clean up temporary file
            temp_path.unlink(missing_ok=True)

            if success:
                return jsonify({"message": message, "stats": stats}), 200
            else:
                return jsonify({"error": message, "stats": stats}), 400
        except Exception as e:
            logger.error(f"Error importing {data_type} data: {str(e)}")
            # Clean up temp file on error too
            if 'temp_path' in locals() and temp_path.exists():
                 temp_path.unlink(missing_ok=True)
            return jsonify({"error": f"Failed to import {data_type} data: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file type, only CSV allowed"}), 400
