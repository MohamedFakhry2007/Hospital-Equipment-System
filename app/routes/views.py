# app/routes/views.py

"""
Frontend routes for rendering HTML pages.
"""
import logging
from dateutil.relativedelta import relativedelta # Keep for now, might be removed if index logic changes enough
import io
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask import send_file
from flask_login import login_required
import tempfile
from app.services.data_service import DataService
from app.services import training_service # Added for training page
from app.services.audit_service import AuditService
from app.constants import DEPARTMENTS, TRAINING_MODULES, QUARTER_STATUS_OPTIONS, GENERAL_STATUS_OPTIONS, DEVICES_BY_DEPARTMENT, ALL_DEVICES, DEPARTMENTS_AND_MACHINES, TRAINERS
from datetime import datetime # Keep datetime
import json
from pathlib import Path

views_bp = Blueprint('views', __name__)
logger = logging.getLogger('app')

# Allowed file extension
ALLOWED_EXTENSIONS = {'csv'}

def calculate_next_quarter_date(base_date_str, months_to_add):
    """
    Calculates the date for the next quarter.

    Args:
        base_date_str (str): The base date string in "DD/MM/YYYY" format.
        months_to_add (int): Number of months to add.

    Returns:
        str: The new date string in "DD/MM/YYYY" format, or None if input is invalid.
    """
    if not base_date_str:
        return None
    try:
        base_date = datetime.strptime(base_date_str, "%d/%m/%Y")
        next_date = base_date + relativedelta(months=months_to_add)
        return next_date.strftime("%d/%m/%Y")
    except ValueError:
        return None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@views_bp.route('/')
@login_required
def index():
    """Display the dashboard with maintenance statistics."""
    """Display the dashboard with maintenance statistics."""
    try:
        ppm_data = DataService.get_all_entries(data_type='ppm')
        ocm_data = DataService.get_all_entries(data_type='ocm')
        
        # Ensure data is a list, even if only one item is returned
        if isinstance(ppm_data, dict):
            ppm_data = [ppm_data]
        if isinstance(ocm_data, dict):
            ocm_data = [ocm_data]

        all_equipment = ppm_data + ocm_data

        total_machines = len(all_equipment)
        ppm_machine_count = len(ppm_data)
        ocm_machine_count = len(ocm_data)

        # Calculate status counts
        overdue_count = 0
        upcoming_count = 0
        maintained_count = 0

        # Calculate upcoming maintenance for OCM (for simplicity, direct check on Next_Maintenance)
        today = datetime.now().date()
        upcoming_7_days = 0
        upcoming_14_days = 0
        upcoming_21_days = 0
        upcoming_30_days = 0
        upcoming_60_days = 0
        upcoming_90_days = 0

        for item in all_equipment:
            status = item.get('Status', 'N/A').lower() # Ensure status is lowercase for comparison

            if status == 'overdue':
                overdue_count += 1
            elif status == 'upcoming':
                upcoming_count += 1
                # For OCM, check Next_Maintenance date
                if item.get('data_type') == 'ocm': # Assuming 'data_type' is added or can be inferred
                    next_maintenance = item.get('Next_Maintenance')
                    if next_maintenance and next_maintenance != 'N/A':
                        try:
                            # Use the flexible date parsing from email service
                            from app.services.email_service import EmailService
                            next_date = EmailService.parse_date_flexible(next_maintenance).date()
                            days_until = (next_date - today).days

                            if days_until <= 7: upcoming_7_days += 1
                            if days_until <= 14: upcoming_14_days += 1
                            if days_until <= 21: upcoming_21_days += 1
                            if days_until <= 30: upcoming_30_days += 1
                            if days_until <= 60: upcoming_60_days += 1
                            if days_until <= 90: upcoming_90_days += 1
                        except (ValueError, ImportError): # Catch specific errors for date parsing
                            logger.warning(f"Could not parse date for OCM item {item.get('Serial')}: {next_maintenance}")
                            pass # Skip if date is invalid

            elif status == 'maintained':
                maintained_count += 1

        stats = {
            'total_machines': total_machines,
            'ppm_machine_count': ppm_machine_count,
            'ocm_machine_count': ocm_machine_count,
            'overdue_count': overdue_count,
            'upcoming_count': upcoming_count,
            'maintained_count': maintained_count,
            'upcoming_7_days': upcoming_7_days,
            'upcoming_14_days': upcoming_14_days,
            'upcoming_21_days': upcoming_21_days,
            'upcoming_30_days': upcoming_30_days,
            'upcoming_60_days': upcoming_60_days,
            'upcoming_90_days': upcoming_90_days,
            'current_time': datetime.now().strftime("%A, %d %B %Y — %H:%M:%S")
        }

        return render_template('dashboard/index.html', title="Dashboard", stats=stats)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash("Error loading dashboard data.", "danger")
        # Provide default stats if loading fails
        default_stats = {
            'total_machines': 0, 'ppm_machine_count': 0, 'ocm_machine_count': 0,
            'overdue_count': 0, 'upcoming_count': 0, 'maintained_count': 0,
            'upcoming_7_days': 0, 'upcoming_14_days': 0, 'upcoming_21_days': 0,
            'upcoming_30_days': 0, 'upcoming_60_days': 0, 'upcoming_90_days': 0,
            'current_time': datetime.now().strftime("%A, %d %B %Y — %H:%M:%S")
        }
        return render_template('dashboard/index.html', title="Dashboard", stats=default_stats)


@views_bp.route('/healthz')
def health_check():
    """Simple health check endpoint."""
    logger.info("Health check endpoint /healthz was accessed.")
    return "OK", 200


@views_bp.route('/equipment/<data_type>/list')
@login_required
def list_equipment(data_type):
    """Display list of equipment (either PPM or OCM)."""
    if data_type not in ('ppm', 'ocm'):
        flash("Invalid equipment type specified.", "warning")
        return redirect(url_for('views.index'))
    try:
        equipment_data = DataService.get_all_entries(data_type)
        for item in equipment_data:
            # Calculate overall status_class
            status = item.get('Status')
            if status is None:
                status = 'N/A'
            else:
                status = status.lower()
                
            if status == 'overdue':
                item['status_class'] = 'danger'
            elif status == 'upcoming':
                item['status_class'] = 'warning'
            elif status == 'maintained':
                item['status_class'] = 'success'
            else:
                item['status_class'] = 'secondary'
            
            # Calculate individual quarter statuses for PPM entries
            if data_type == 'ppm':
                today = datetime.now().date()
                quarter_keys = ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']
                
                for q_key in quarter_keys:
                    quarter_info = item.get(q_key, {})
                    if isinstance(quarter_info, dict):
                        quarter_date_str = quarter_info.get('quarter_date')
                        engineer = quarter_info.get('engineer')
                        engineer = engineer.strip() if engineer else ''
                        
                        if quarter_date_str:
                            try:
                                # Use the flexible date parsing from email service
                                from app.services.email_service import EmailService
                                quarter_date = EmailService.parse_date_flexible(quarter_date_str).date()
                                
                                # Calculate status based on date and engineer
                                if quarter_date < today:
                                    if engineer and engineer.strip():  # Check for non-empty engineer
                                        quarter_status = 'Maintained'
                                        status_class = 'success'
                                    else:
                                        quarter_status = 'Overdue'
                                        status_class = 'danger'
                                elif quarter_date == today:
                                    quarter_status = 'Maintained'
                                    status_class = 'success'
                                else:
                                    quarter_status = 'Upcoming'
                                    status_class = 'warning'
                                
                                # Update the quarter info
                                quarter_info['status'] = quarter_status
                                quarter_info['status_class'] = status_class
                                
                            except (ValueError, ImportError):
                                # Invalid date format or import error, set default
                                quarter_info['status'] = 'N/A'
                                quarter_info['status_class'] = 'secondary'
                        else:
                            # No date specified
                            quarter_info['status'] = 'N/A'
                            quarter_info['status_class'] = 'secondary'
        
        return render_template('equipment/list.html', equipment=equipment_data, data_type=data_type)
    except Exception as e:
        logger.error(f"Error loading {data_type} list: {str(e)}")
        flash(f"Error loading {data_type.upper()} equipment data.", "danger")
        return render_template('equipment/list.html', equipment=[], data_type=data_type)


@views_bp.route('/equipment/ppm/add', methods=['GET', 'POST'])
@login_required
def add_ppm_equipment():
    """Handle adding new PPM equipment."""
    if request.method == 'POST':
        form_data = request.form.to_dict()

        # Get quarter dates from form (frontend calculates these)
        q1_date_to_store = form_data.get("PPM_Q_I_date", "").strip() or None
        q2_date_str = form_data.get("PPM_Q_II_date", "").strip() or None
        q3_date_str = form_data.get("PPM_Q_III_date", "").strip() or None
        q4_date_str = form_data.get("PPM_Q_IV_date", "").strip() or None

        # Structure data for PPMEntry model
        # PPM_Q_X fields expect {"engineer": "name"}
        ppm_data = {
            "MODEL": form_data.get("MODEL"),
            "Name": form_data.get("Name"), # Optional
            "SERIAL": form_data.get("SERIAL"),
            "MANUFACTURER": form_data.get("MANUFACTURER"),
            "Department": form_data.get("Department"),
            "LOG_Number": form_data.get("LOG_Number"),            "Installation_Date": form_data.get("Installation_Date", "").strip() or None,
            "Warranty_End": form_data.get("Warranty_End", "").strip() or None,
            "PPM_Q_I": {
                "engineer": form_data.get("PPM_Q_I_engineer", "").strip() or None,
                "quarter_date": form_data.get("PPM_Q_I_date", "").strip() or None,
                "status": form_data.get("PPM_Q_I_status", "").strip() or None
            },
            "PPM_Q_II": {
                "engineer": form_data.get("PPM_Q_II_engineer", "").strip() or None,
                "quarter_date": form_data.get("PPM_Q_II_date", "").strip() or None,
                "status": form_data.get("PPM_Q_II_status", "").strip() or None
            },
            "PPM_Q_III": {
                "engineer": form_data.get("PPM_Q_III_engineer", "").strip() or None,
                "quarter_date": form_data.get("PPM_Q_III_date", "").strip() or None,
                "status": form_data.get("PPM_Q_III_status", "").strip() or None
            },
            "PPM_Q_IV": {
                "engineer": form_data.get("PPM_Q_IV_engineer", "").strip() or None,
                "quarter_date": form_data.get("PPM_Q_IV_date", "").strip() or None,
                "status": form_data.get("PPM_Q_IV_status", "").strip() or None
            }
        }
        # Ensure Name is None if empty, not just for "if not ppm_data['Name']" which might fail if key missing
        if ppm_data.get("Name") == "":
            ppm_data["Name"] = None

        try:
            DataService.add_entry('ppm', ppm_data)
            flash('PPM equipment added successfully!', 'success')
            return redirect(url_for('views.list_equipment', data_type='ppm'))
        except ValueError as e:
            flash(f"Error adding equipment: {str(e)}", 'danger')
            # Re-render form with submitted data and errors (errors flashed)
            return render_template('equipment/add_ppm.html', data_type='ppm', form_data=form_data, 
                                 departments=DEPARTMENTS, quarter_status_options=QUARTER_STATUS_OPTIONS)
        except Exception as e:
            logger.error(f"Error adding PPM equipment: {str(e)}")
            flash('An unexpected error occurred while adding.', 'danger')
            return render_template('equipment/add_ppm.html', data_type='ppm', form_data=form_data,
                                 departments=DEPARTMENTS, quarter_status_options=QUARTER_STATUS_OPTIONS)

    # GET request: show empty form
    return render_template('equipment/add_ppm.html', data_type='ppm', form_data={},
                         departments=DEPARTMENTS, quarter_status_options=QUARTER_STATUS_OPTIONS)

@views_bp.route('/equipment/ocm/add', methods=['GET', 'POST'])
@login_required
def add_ocm_equipment():
    """Handle adding new OCM equipment."""
    if request.method == 'POST':
        form_data = request.form.to_dict()
        ocm_data = {
            "Department": form_data.get("Department"),
            "Name": form_data.get("Name"),
            "Model": form_data.get("Model"),
            "Serial": form_data.get("Serial"),
            "Manufacturer": form_data.get("Manufacturer"),
            "Log_Number": form_data.get("Log_Number"),
            "Installation_Date": form_data.get("Installation_Date"),
            "Warranty_End": form_data.get("Warranty_End"),
            "Service_Date": form_data.get("Service_Date"),
            "Engineer": form_data.get("Engineer"),
            "Next_Maintenance": form_data.get("Next_Maintenance"),
            "Status": form_data.get("Status")
        }

        try:
            DataService.add_entry('ocm', ocm_data)
            flash('OCM equipment added successfully!', 'success')
            return redirect(url_for('views.list_equipment', data_type='ocm'))
        except ValueError as e:
            flash(f"Error adding equipment: {str(e)}", 'danger')
            return render_template('equipment/add_ocm.html', data_type='ocm', form_data=form_data, departments=DEPARTMENTS, general_status_options=GENERAL_STATUS_OPTIONS)
        except Exception as e:
            logger.error(f"Error adding OCM equipment: {str(e)}")
            flash('An unexpected error occurred while adding.', 'danger')
            return render_template('equipment/add_ocm.html', data_type='ocm', form_data=form_data, departments=DEPARTMENTS, general_status_options=GENERAL_STATUS_OPTIONS)

    return render_template('equipment/add_ocm.html', data_type='ocm', form_data={}, departments=DEPARTMENTS, general_status_options=GENERAL_STATUS_OPTIONS)


@views_bp.route('/equipment/ppm/edit/<SERIAL>', methods=['GET', 'POST'])
@login_required
def edit_ppm_equipment(SERIAL):
    """Handle editing existing PPM equipment."""
    entry = DataService.get_entry('ppm', SERIAL)
    if not entry:
        flash(f"PPM Equipment with serial '{SERIAL}' not found.", 'warning')
        return redirect(url_for('views.list_equipment', data_type='ppm'))

    if request.method == 'POST':
        form_data = request.form.to_dict()
        ppm_data_update = {
            "MODEL": form_data.get("MODEL"),
            "Name": form_data.get("Name"),
            "SERIAL": SERIAL, # Should not change
            "MANUFACTURER": form_data.get("MANUFACTURER"),
            "Department": form_data.get("Department"),
            "LOG_Number": form_data.get("LOG_Number"),
            "Installation_Date": form_data.get("Installation_Date", "").strip() or None,
            "Warranty_End": form_data.get("Warranty_End", "").strip() or None,
            # Individual quarter data with status
            "PPM_Q_I": {
                "engineer": form_data.get("PPM_Q_I_engineer", "").strip() or None,
                "quarter_date": form_data.get("PPM_Q_I_date", "").strip() or None,
                "status": form_data.get("PPM_Q_I_status", "").strip() or None
            },
            "PPM_Q_II": {
                "engineer": form_data.get("PPM_Q_II_engineer", "").strip() or None,
                "quarter_date": form_data.get("PPM_Q_II_date", "").strip() or None,
                "status": form_data.get("PPM_Q_II_status", "").strip() or None
            },
            "PPM_Q_III": {
                "engineer": form_data.get("PPM_Q_III_engineer", "").strip() or None,
                "quarter_date": form_data.get("PPM_Q_III_date", "").strip() or None,
                "status": form_data.get("PPM_Q_III_status", "").strip() or None
            },
            "PPM_Q_IV": {
                "engineer": form_data.get("PPM_Q_IV_engineer", "").strip() or None,
                "quarter_date": form_data.get("PPM_Q_IV_date", "").strip() or None,
                "status": form_data.get("PPM_Q_IV_status", "").strip() or None
            },
        }
        if ppm_data_update.get("Name") == "":
            ppm_data_update["Name"] = None

        # Calculate overall status based on individual quarter statuses
        calculated_status = DataService.calculate_status(ppm_data_update, 'ppm')
        ppm_data_update['Status'] = calculated_status

        try:
            DataService.update_entry('ppm', SERIAL, ppm_data_update)
            flash('PPM equipment updated successfully!', 'success')
            return redirect(url_for('views.list_equipment', data_type='ppm'))
        except ValueError as e:
            flash(f"Error updating equipment: {str(e)}", 'danger')
        except KeyError: # Should not typically be raised by DataService.update_entry for not found.
             flash(f"Equipment with serial '{SERIAL}' not found for update.", 'warning')
             return redirect(url_for('views.list_equipment', data_type='ppm'))
        except Exception as e:
            logger.error(f"Error updating PPM equipment {SERIAL}: {str(e)}")
            flash('An unexpected error occurred during update.', 'danger')

        # Re-render form on POST error: use form_data directly for field values
        return render_template('equipment/edit_ppm.html', data_type='ppm', entry=entry, departments=DEPARTMENTS)

    # GET request: Populate form with existing data
    return render_template('equipment/edit_ppm.html', data_type='ppm', entry=entry, departments=DEPARTMENTS)


@views_bp.route('/equipment/ocm/edit/<Serial>', methods=['GET', 'POST'])
@login_required
def edit_ocm_equipment(Serial):
    """Handle editing OCM equipment."""
    logger.info(f"Received {request.method} request to edit OCM equipment with Serial: {Serial}")
    
    try:
        logger.debug(f"Attempting to fetch OCM entry with Serial: {Serial}")
        entry = DataService.get_entry('ocm', Serial)
        logger.debug(f"DataService.get_entry result: {entry}")
        
        if not entry:
            logger.warning(f"OCM Equipment with Serial '{Serial}' not found in database")
            flash(f"Equipment with Serial '{Serial}' not found.", 'warning')
            return redirect(url_for('views.list_equipment', data_type='ocm'))

        if request.method == 'POST':
            logger.info(f"Processing POST request for OCM Serial: {Serial}")
            form_data = request.form.to_dict()
            logger.debug(f"Received form data: {form_data}")
            
            # Preserve the NO field from the original entry
            ocm_data = {
                "NO": entry["NO"],  # Preserve the original NO
                "Department": form_data.get("Department"),
                "Name": form_data.get("Name"),
                "Model": form_data.get("Model"),
                "Serial": Serial,  # Use the original Serial from URL
                "Manufacturer": form_data.get("Manufacturer"),
                "Log_Number": form_data.get("Log_Number"),
                "Installation_Date": form_data.get("Installation_Date"),
                "Warranty_End": form_data.get("Warranty_End"),
                "Service_Date": form_data.get("Service_Date"),
                "Engineer": form_data.get("Engineer"),
                "Next_Maintenance": form_data.get("Next_Maintenance"),
                "Status": form_data.get("Status")
            }
            logger.debug(f"Constructed OCM data for update: {ocm_data}")

            try:
                logger.info(f"Attempting to update OCM entry with Serial: {Serial}")
                DataService.update_entry('ocm', Serial, ocm_data)
                logger.info(f"Successfully updated OCM equipment with Serial: {Serial}")
                flash('OCM equipment updated successfully!', 'success')
                return redirect(url_for('views.list_equipment', data_type='ocm'))
            except ValueError as e:
                logger.error(f"Validation error while updating OCM equipment {Serial}: {str(e)}")
                flash(f"Error updating equipment: {str(e)}", 'danger')
                return render_template('equipment/edit_ocm.html', data_type='ocm', entry=form_data, departments=DEPARTMENTS)
            except Exception as e:
                logger.error(f"Unexpected error updating OCM equipment {Serial}: {str(e)}", exc_info=True)
                flash('An unexpected error occurred while updating.', 'danger')
                return render_template('equipment/edit_ocm.html', data_type='ocm', entry=form_data, departments=DEPARTMENTS)

        logger.debug(f"Rendering edit form for OCM equipment {Serial} with data: {entry}")
        return render_template('equipment/edit_ocm.html', data_type='ocm', entry=entry, departments=DEPARTMENTS)

    except Exception as e:
        logger.error(f"Critical error in edit_ocm_equipment for Serial {Serial}: {str(e)}", exc_info=True)
        flash('An unexpected error occurred.', 'danger')
        return redirect(url_for('views.list_equipment', data_type='ocm'))


@views_bp.route('/equipment/<data_type>/delete/<path:SERIAL>', methods=['POST'])
@login_required
def delete_equipment(data_type, SERIAL):
    """Handle deleting existing equipment."""
    logger.info(f"Received request to delete {data_type} equipment with serial: {SERIAL}")
    
    if data_type not in ('ppm', 'ocm'):
        logger.warning(f"Invalid data type specified: {data_type}")
        flash("Invalid equipment type specified.", "warning")
        return redirect(url_for('views.index'))

    try:
        # First verify the equipment exists
        logger.debug(f"Verifying {data_type} equipment exists with serial: {SERIAL}")
        entry = DataService.get_entry(data_type, SERIAL)
        
        if not entry:
            logger.warning(f"{data_type.upper()} equipment with serial '{SERIAL}' not found before deletion")
            flash(f"{data_type.upper()} equipment '{SERIAL}' not found.", 'warning')
            return redirect(url_for('views.list_equipment', data_type=data_type))
            
        # Proceed with deletion
        logger.info(f"Attempting to delete {data_type} equipment with serial: {SERIAL}")
        deleted = DataService.delete_entry(data_type, SERIAL)
        
        if deleted:
            logger.info(f"Successfully deleted {data_type} equipment with serial: {SERIAL}")
            flash(f'{data_type.upper()} equipment \'{SERIAL}\' deleted successfully!', 'success')
        else:
            # This should not happen since we verified existence, but handle it just in case
            logger.error(f"Unexpected: {data_type} equipment with serial '{SERIAL}' not found during deletion despite existing")
            flash(f'{data_type.upper()} equipment \'{SERIAL}\' not found.', 'warning')
            
    except Exception as e:
        logger.error(f"Error deleting {data_type} equipment {SERIAL}: {str(e)}", exc_info=True)
        flash('An unexpected error occurred during deletion.', 'danger')

    return redirect(url_for('views.list_equipment', data_type=data_type))

# --- Import/Export Routes ---

@views_bp.route('/import-export')
@login_required
def import_export_page():
    """Display the import/export page."""
    return render_template('import_export/main.html')

@views_bp.route('/import_equipment', methods=['POST'])
@login_required
def import_equipment():
    """Import equipment data from CSV file."""
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('views.import_export_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('views.import_export_page'))

    # Get the data type from the form
    data_type = request.form.get('data_type', '').strip()
    if data_type not in ['ppm', 'ocm', 'training']:
        flash('Invalid data type specified', 'error')
        return redirect(url_for('views.import_export_page'))

    if file and allowed_file(file.filename):
        try:
            logger.info(f"Starting import_equipment process for {data_type} data")
            logger.info(f"Processing file: {file.filename}")

            # Save the file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name

            # Import using the specified data type
            from app.services.import_export import ImportExportService
            success, message, stats = ImportExportService.import_from_csv(data_type, temp_path)
            
            # Clean up temporary file
            import os
            os.unlink(temp_path)
            
            if success:
                flash(f'{data_type.upper()} import successful: {message}', 'success')
                logger.info(f"Import successful for {data_type}, redirecting...")
                
                # Check if this is an AJAX request (for training)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                    logger.info("AJAX request detected, returning JSON response")
                    return jsonify({
                        'success': True,
                        'message': message,
                        'redirect_url': '/training' if data_type == 'training' else f'/equipment/{data_type}'
                    })
                
                # Regular form submission - redirect
                if data_type == 'training':
                    logger.info("Redirecting to training management page")
                    return redirect(url_for('views.training_management_page'))
                elif data_type in ['ppm', 'ocm']:
                    logger.info(f"Redirecting to {data_type} equipment list page")
                    return redirect(url_for('views.list_equipment', data_type=data_type))
                else:
                    logger.info("Redirecting to import export page (fallback)")
                    return redirect(url_for('views.import_export_page'))
            else:
                flash(f'{data_type.upper()} import failed: {message}', 'error')
                logger.error(f"Import failed for {data_type}: {message}")
                
                # Check if this is an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                    return jsonify({'success': False, 'error': message}), 400
                
                return redirect(url_for('views.import_export_page'))

        except Exception as e:
            logger.error(f"Error during {data_type} import: {str(e)}")
            flash(f'Error during {data_type} import: {str(e)}', 'error')
            return redirect(url_for('views.import_export_page'))

    flash('Invalid file type', 'error')
    return redirect(url_for('views.import_export_page'))


@views_bp.route('/export/ppm')
@login_required
def export_equipment_ppm():
    """Export PPM equipment data to CSV."""
    try:
        logger.info("Starting PPM data export process")
        csv_content = DataService.export_data(data_type='ppm')
        logger.debug("PPM data retrieved from DataService")

        # Use BytesIO for in-memory file handling with send_file
        mem_file = io.BytesIO()
        mem_file.write(csv_content.encode('utf-8'))
        mem_file.seek(0)
        logger.debug("CSV content written to memory buffer")

        filename = f"ppm_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        logger.info(f"Sending PPM export file: {filename}")
        
        return send_file(
            mem_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        error_msg = f"Error exporting PPM data: {str(e)}"
        logger.exception(error_msg)
        flash(error_msg, 'danger')
        return redirect(url_for('views.import_export_page'))

@views_bp.route('/export/ocm')
@login_required
def export_equipment_ocm():
    """Export OCM equipment data to CSV."""
    try:
        csv_content = DataService.export_data(data_type='ocm')
        mem_file = io.BytesIO()
        mem_file.write(csv_content.encode('utf-8'))
        mem_file.seek(0)
        return send_file(
            mem_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name='ocm_export.csv'
        )
    except Exception as e:
        logger.exception("Error exporting OCM data.")
        flash(f"An error occurred during OCM export: {str(e)}", 'danger')
        return redirect(url_for('views.import_export_page'))

@views_bp.route('/export/training')
@login_required
def export_equipment_training():
    """Export Training data to CSV."""
    try:
        logger.info("Starting Training data export process")
        csv_content = DataService.export_data(data_type='training')
        logger.debug("Training data retrieved from DataService")

        # Use BytesIO for in-memory file handling with send_file
        mem_file = io.BytesIO()
        mem_file.write(csv_content.encode('utf-8'))
        mem_file.seek(0)
        logger.debug("CSV content written to memory buffer")

        filename = f"training_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        logger.info(f"Sending Training export file: {filename}")
        
        return send_file(
            mem_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        error_msg = f"Error exporting Training data: {str(e)}"
        logger.exception(error_msg)
        flash(error_msg, 'danger')
        return redirect(url_for('views.import_export_page'))

@views_bp.route('/download/template/<template_type>')
@login_required
def download_template(template_type):
    """Download template files for data import."""
    try:
        if template_type not in ['ppm', 'ocm', 'training']:
            flash("Invalid template type specified.", "warning")
            return redirect(url_for('views.import_export_page'))
        
        # Use Flask's built-in template system to find the correct path
        import os
        from flask import current_app
        
        # Use current_app.root_path to get the app directory correctly
        app_root = current_app.root_path
        template_path = os.path.join(app_root, "templates", "csv", f"{template_type}_template.csv")
        filename = f"{template_type}_template.csv"
        
        # Debug logging to see what path is being constructed
        logger.info(f"App root path: {app_root}")
        logger.info(f"Constructed template path: {template_path}")
        logger.info(f"File exists: {os.path.exists(template_path)}")
        
        if not os.path.exists(template_path):
            error_msg = f"Template file not found: {template_path}"
            logger.error(error_msg)
            flash(error_msg, 'danger')
            return redirect(url_for('views.import_export_page'))
        
        return send_file(
            template_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        error_msg = f"Error downloading {template_type} template: {str(e)}"
        logger.exception(error_msg)
        flash(error_msg, 'danger')
        return redirect(url_for('views.import_export_page'))

@views_bp.route('/settings')
@login_required
def settings_page():
    """Display the settings page."""
    settings = DataService.load_settings()
    return render_template('settings.html', settings=settings)

settings_bp = Blueprint('settings', __name__)
SETTINGS_FILE = Path("data/settings.json")


@settings_bp.route('/settings', methods=['GET'])
def settings_page():
    # Load current settings
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    else:
        settings = {}

    return render_template('settings.html', settings=settings)


@settings_bp.route('/settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return jsonify({"message": "Settings updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views_bp.route('/settings', methods=['POST'])
def save_settings_page():
    """Handle saving settings."""
    logger.info("Received request to save settings.")

    if not request.is_json:
        logger.warning("Request format is not JSON.")
        flash('Invalid request format. Expected JSON.', 'danger')
        return redirect(url_for('views.settings_page'))

    data = request.get_json()
    logger.debug(f"Request data: {data}")

    # Extract and validate data
    email_notifications_enabled = data.get('email_notifications_enabled', False)
    logger.debug(f"Email notifications enabled: {email_notifications_enabled}")

    try:
        email_reminder_interval_minutes = int(data.get('email_reminder_interval_minutes'))
        if email_reminder_interval_minutes <= 0:
            logger.warning("Invalid email reminder interval: must be a positive number.")
            flash('Email reminder interval must be a positive number.', 'danger')
            return redirect(url_for('views.settings_page'))
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing email reminder interval: {e}")
        flash('Invalid value for email reminder interval. Please enter a positive number.', 'danger')
        return redirect(url_for('views.settings_page'))

    try:
        email_send_time_hour = int(data.get('email_send_time_hour', 7))
        if email_send_time_hour < 0 or email_send_time_hour > 23:
            logger.warning("Invalid email send time hour: must be between 0-23.")
            flash('Email send time must be between 0-23 hours.', 'danger')
            return redirect(url_for('views.settings_page'))
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing email send time hour: {e}")
        flash('Invalid value for email send time hour. Please enter a number between 0-23.', 'danger')
        return redirect(url_for('views.settings_page'))

    recipient_email = data.get('recipient_email', '').strip()
    logger.debug(f"Recipient email: {recipient_email}")

    push_notifications_enabled = data.get('push_notifications_enabled', False)
    logger.debug(f"Push notifications enabled: {push_notifications_enabled}")

    try:
        push_notification_interval_minutes = int(data.get('push_notification_interval_minutes'))
        if push_notification_interval_minutes <= 0:
            logger.warning("Invalid push notification interval: must be a positive number.")
            flash('Push notification interval must be a positive number.', 'danger')
            return redirect(url_for('views.settings_page'))
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing push notification interval: {e}")
        flash('Invalid value for push notification interval. Please enter a positive number.', 'danger')
        return redirect(url_for('views.settings_page'))

    # Update settings
    current_settings = DataService.load_settings()
    logger.info("Loaded current settings.")

    # Handle new settings fields
    reminder_timing_60_days = data.get('reminder_timing_60_days', False)
    reminder_timing_14_days = data.get('reminder_timing_14_days', False)
    reminder_timing_1_day = data.get('reminder_timing_1_day', False)
    
    try:
        scheduler_interval_hours = int(data.get('scheduler_interval_hours', 24))
        if scheduler_interval_hours <= 0 or scheduler_interval_hours > 168:
            logger.warning("Invalid scheduler interval: must be between 1-168 hours.")
            flash('Scheduler interval must be between 1-168 hours.', 'danger')
            return redirect(url_for('views.settings_page'))
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing scheduler interval: {e}")
        flash('Invalid value for scheduler interval. Please enter a number between 1-168.', 'danger')
        return redirect(url_for('views.settings_page'))
    
    enable_automatic_reminders = data.get('enable_automatic_reminders', False)
    cc_emails = data.get('cc_emails', '').strip()

    # Handle backup settings
    automatic_backup_enabled = data.get('automatic_backup_enabled', False)
    try:
        automatic_backup_interval_hours = int(data.get('automatic_backup_interval_hours', 24))
        if automatic_backup_interval_hours < 1 or automatic_backup_interval_hours > 168:
            logger.warning("Invalid backup interval: must be between 1-168 hours.")
            flash('Backup interval must be between 1-168 hours.', 'danger')
            return redirect(url_for('views.settings_page'))
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing backup interval: {e}")
        flash('Invalid value for backup interval. Please enter a number between 1-168.', 'danger')
        return redirect(url_for('views.settings_page'))

    current_settings.update({
        'email_notifications_enabled': email_notifications_enabled,
        'email_reminder_interval_minutes': email_reminder_interval_minutes,
        'email_send_time_hour': email_send_time_hour,
        'recipient_email': recipient_email,
        'push_notifications_enabled': push_notifications_enabled,
        'push_notification_interval_minutes': push_notification_interval_minutes,
        'reminder_timing': {
            '60_days_before': reminder_timing_60_days,
            '14_days_before': reminder_timing_14_days,
            '1_day_before': reminder_timing_1_day
        },
        'scheduler_interval_hours': scheduler_interval_hours,
        'enable_automatic_reminders': enable_automatic_reminders,
        'cc_emails': cc_emails,
        'automatic_backup_enabled': automatic_backup_enabled,
        'automatic_backup_interval_hours': automatic_backup_interval_hours
    })
    logger.info(f"Updated settings: {current_settings}")

    try:
        DataService.save_settings(current_settings)
        logger.info("Settings saved successfully.")
        flash('Settings saved successfully!', 'success')
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        flash('An error occurred while saving settings.', 'danger')

    return redirect(url_for('views.settings_page'))


@views_bp.route('/settings/reminder', methods=['POST'])
@login_required
def save_reminder_settings():
    """Handle saving reminder-specific settings."""
    logger.info("Received request to save reminder settings.")
    
    if not request.is_json:
        logger.warning("Request format is not JSON.")
        return jsonify({'error': 'Invalid request format. Expected JSON.'}), 400
    
    data = request.get_json()
    logger.debug(f"Reminder settings data: {data}")
    
    try:
        # Validate scheduler interval
        scheduler_interval_hours = int(data.get('scheduler_interval_hours', 24))
        if scheduler_interval_hours <= 0 or scheduler_interval_hours > 168:
            return jsonify({'error': 'Scheduler interval must be between 1-168 hours.'}), 400
        
        # Load current settings and update reminder-specific fields
        current_settings = DataService.load_settings()
        current_settings.update({
            'reminder_timing': {
                '60_days_before': data.get('reminder_timing_60_days', False),
                '14_days_before': data.get('reminder_timing_14_days', False),
                '1_day_before': data.get('reminder_timing_1_day', False)
            },
            'scheduler_interval_hours': scheduler_interval_hours,
            'enable_automatic_reminders': data.get('enable_automatic_reminders', False)
        })
        
        DataService.save_settings(current_settings)
        logger.info("Reminder settings saved successfully.")
        return jsonify({'message': 'Reminder settings saved successfully!'}), 200
        
    except Exception as e:
        logger.error(f"Error saving reminder settings: {str(e)}")
        return jsonify({'error': 'An error occurred while saving reminder settings.'}), 500


@views_bp.route('/settings/email', methods=['POST'])
@login_required
def save_email_settings():
    """Handle saving email-specific settings."""
    logger.info("Received request to save email settings.")
    
    if not request.is_json:
        logger.warning("Request format is not JSON.")
        return jsonify({'error': 'Invalid request format. Expected JSON.'}), 400
    
    data = request.get_json()
    logger.debug(f"Email settings data: {data}")
    
    try:
        # Load current settings and update email-specific fields
        current_settings = DataService.load_settings()
        current_settings.update({
            'recipient_email': data.get('recipient_email', '').strip(),
            'cc_emails': data.get('cc_emails', '').strip()
        })
        
        DataService.save_settings(current_settings)
        logger.info("Email settings saved successfully.")
        return jsonify({'message': 'Email settings saved successfully!'}), 200
        
    except Exception as e:
        logger.error(f"Error saving email settings: {str(e)}")
        return jsonify({'error': 'An error occurred while saving email settings.'}), 500


@views_bp.route('/settings/test-email', methods=['POST'])
@login_required
def send_test_email():
    """Send a test email to verify email configuration."""
    logger.info("Received request to send test email.")
    
    try:
        from app.services.email_service import EmailService
        
        # Load current settings
        settings = DataService.load_settings()
        recipient_email = settings.get('recipient_email', '')
        cc_emails = settings.get('cc_emails', '')
        
        if not recipient_email:
            return jsonify({'error': 'No recipient email configured.'}), 400
        
        # Prepare test email content
        subject = "Hospital Equipment System - Test Email"
        body = f"""
        <h2>Test Email from Hospital Equipment System</h2>
        <p>This is a test email to verify your email configuration.</p>
        <p><strong>Sent to:</strong> {recipient_email}</p>
        {f'<p><strong>CC:</strong> {cc_emails}</p>' if cc_emails else ''}
        <p><strong>Sent at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>If you received this email, your email settings are working correctly!</p>
        """
        
        # Prepare recipient list
        recipients = [recipient_email]
        if cc_emails:
            cc_list = [email.strip() for email in cc_emails.split(',') if email.strip()]
            recipients.extend(cc_list)
        
        # Send test email (using existing email service)
        # Note: This assumes EmailService has a method to send immediate emails
        # If not, we may need to implement a simple email sending function
        success = EmailService.send_immediate_email(recipients, subject, body)
        
        if success:
            logger.info(f"Test email sent successfully to {recipients}")
            return jsonify({'message': 'Test email sent successfully!'}), 200
        else:
            logger.error("Failed to send test email")
            return jsonify({'error': 'Failed to send test email. Please check your email configuration.'}), 500
            
    except ImportError:
        logger.error("EmailService not available")
        return jsonify({'error': 'Email service not available.'}), 500
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        return jsonify({'error': f'Error sending test email: {str(e)}'}), 500


# Training Management Page
@views_bp.route('/training')
@login_required
def training_management_page():
    """Display the training management page."""
    logger.info("Training management page accessed")
    try:
        all_trainings = training_service.get_all_trainings()
        logger.info(f"Loaded {len(all_trainings)} training records")
        # Convert Training objects to dicts if necessary for the template,
        # or ensure template handles objects. Assuming template handles objects with attributes.
        return render_template('training/list.html', 
                             trainings=all_trainings,
                             departments=DEPARTMENTS,
                             training_modules=TRAINING_MODULES,
                             trainers=TRAINERS,
                             devices_by_department=DEVICES_BY_DEPARTMENT,
                             all_devices=ALL_DEVICES)
    except Exception as e:
        logger.error(f"Error loading training management page: {str(e)}", exc_info=True)
        flash("Error loading training data.", "danger")
        return render_template('training/list.html', 
                             trainings=[],
                             departments=DEPARTMENTS,
                             training_modules=TRAINING_MODULES,
                             trainers=TRAINERS,
                             devices_by_department=DEVICES_BY_DEPARTMENT,
                             all_devices=ALL_DEVICES)

# Barcode Generation Routes
@views_bp.route('/equipment/<data_type>/<serial>/barcode')
@login_required
def generate_barcode(data_type, serial):
    """Generate and display barcode for a specific equipment."""
    from app.services.barcode_service import BarcodeService
    
    try:
        # Get equipment details
        equipment = DataService.get_entry(data_type, serial)
        if not equipment:
            flash(f"Equipment with serial '{serial}' not found.", 'warning')
            return redirect(url_for('views.list_equipment', data_type=data_type))
        
        # Generate barcode
        barcode_base64 = BarcodeService.generate_barcode_base64(serial)
        
        return render_template('equipment/barcode.html', 
                             equipment=equipment, 
                             barcode_base64=barcode_base64,
                             data_type=data_type,
                             serial=serial)
    except Exception as e:
        logger.error(f"Error generating barcode for {serial}: {str(e)}")
        flash('Error generating barcode.', 'danger')
        return redirect(url_for('views.list_equipment', data_type=data_type))

@views_bp.route('/equipment/<data_type>/<serial>/barcode/download')
@login_required
def download_barcode(data_type, serial):
    """Download barcode image for a specific equipment."""
    from app.services.barcode_service import BarcodeService
    
    try:
        # Get equipment details
        equipment = DataService.get_entry(data_type, serial)
        if not equipment:
            flash(f"Equipment with serial '{serial}' not found.", 'warning')
            return redirect(url_for('views.list_equipment', data_type=data_type))
        
        # Generate printable barcode
        equipment_name = equipment.get('Name') or equipment.get('MODEL') or equipment.get('Model')
        department = equipment.get('Department')
        
        barcode_bytes = BarcodeService.generate_printable_barcode(
            serial, equipment_name, department
        )
        
        # Create file-like object
        barcode_file = io.BytesIO(barcode_bytes)
        barcode_file.seek(0)
        
        return send_file(
            barcode_file,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'barcode_{serial}.png'
        )
    except Exception as e:
        logger.error(f"Error downloading barcode for {serial}: {str(e)}")
        flash('Error downloading barcode.', 'danger')
        return redirect(url_for('views.list_equipment', data_type=data_type))

@views_bp.route('/equipment/<data_type>/barcodes/bulk')
@login_required
def bulk_barcodes(data_type):
    """Generate bulk barcodes for all equipment of a specific type."""
    from app.services.barcode_service import BarcodeService
    
    try:
        # Get all equipment
        equipment_list = DataService.get_all_entries(data_type)
        
        barcodes = []
        for equipment in equipment_list:
            serial = equipment.get('SERIAL') if data_type == 'ppm' else equipment.get('Serial')
            if serial:
                try:
                    barcode_base64 = BarcodeService.generate_barcode_base64(serial)
                    barcodes.append({
                        'equipment': equipment,
                        'barcode_base64': barcode_base64,
                        'serial': serial
                    })
                except Exception as e:
                    logger.error(f"Error generating barcode for {serial}: {str(e)}")
        
        return render_template('equipment/bulk_barcodes.html', 
                             barcodes=barcodes,
                             data_type=data_type)
    except Exception as e:
        logger.error(f"Error generating bulk barcodes for {data_type}: {str(e)}")
        flash('Error generating bulk barcodes.', 'danger')
        return redirect(url_for('views.list_equipment', data_type=data_type))

@views_bp.route('/equipment/<data_type>/barcodes/bulk/download')
@login_required
def download_bulk_barcodes(data_type):
    """Download all barcodes as a ZIP file."""
    from app.services.barcode_service import BarcodeService
    import zipfile
    
    try:
        # Get all equipment
        equipment_list = DataService.get_all_entries(data_type)
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for equipment in equipment_list:
                serial = equipment.get('SERIAL') if data_type == 'ppm' else equipment.get('Serial')
                if serial:
                    try:
                        equipment_name = equipment.get('Name') or equipment.get('MODEL') or equipment.get('Model')
                        department = equipment.get('Department')
                        
                        barcode_bytes = BarcodeService.generate_printable_barcode(
                            serial, equipment_name, department
                        )
                        
                        # Add to ZIP
                        zip_file.writestr(f'barcode_{serial}.png', barcode_bytes)
                    except Exception as e:
                        logger.error(f"Error generating barcode for {serial}: {str(e)}")
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{data_type}_barcodes.zip'
        )
    except Exception as e:
        logger.error(f"Error downloading bulk barcodes for {data_type}: {str(e)}")
        flash('Error downloading bulk barcodes.', 'danger')
        return redirect(url_for('views.list_equipment', data_type=data_type))


# Machine Assignment Route
@views_bp.route('/equipment/machine-assignment')
@login_required
def machine_assignment():
    """Display the machine assignment page."""
    return render_template('equipment/machine_assignment.html',
                         departments=DEPARTMENTS,
                         training_modules=TRAINING_MODULES,
                         devices_by_department=DEVICES_BY_DEPARTMENT,
                         trainers=TRAINERS)

@views_bp.route('/equipment/machine-assignment', methods=['POST'])
@login_required
def save_machine_assignment():
    """Save machine assignments."""
    try:
        data = request.get_json()
        assignments = data.get('assignments', [])
        
        # Here you would typically save the assignments to the database
        # For now, we'll just log them
        logger.info(f"Machine assignments saved: {assignments}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully saved {len(assignments)} machine assignments.'
        })
    except Exception as e:
        logger.error(f"Error saving machine assignments: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error saving machine assignments.'
        }), 500

@views_bp.route('/refresh-dashboard')
@login_required
def refresh_dashboard():
    """AJAX endpoint to refresh dashboard data."""
    try:
        # Fetch fresh data
        ppm_data = DataService.get_all_entries(data_type='ppm')
        if isinstance(ppm_data, dict):
            ppm_data = [ppm_data]
        
        ocm_data = DataService.get_all_entries(data_type='ocm')
        if isinstance(ocm_data, dict):
            ocm_data = [ocm_data]
        
        all_equipment = ppm_data + ocm_data
        today = datetime.now().date()
        
        # Calculate fresh statistics
        total_machines = len(all_equipment)
        overdue_count = 0
        upcoming_count = 0
        maintained_count = 0
        upcoming_7_days = 0
        upcoming_14_days = 0
        upcoming_21_days = 0
        upcoming_30_days = 0
        upcoming_60_days = 0
        upcoming_90_days = 0
        
        for item in all_equipment:
            status = item.get('Status', 'N/A').lower()
            
            if status == 'overdue':
                overdue_count += 1
            elif status == 'upcoming':
                upcoming_count += 1
                
                # Calculate upcoming periods
                if item.get('data_type') == 'ocm':
                    next_maintenance = item.get('Next_Maintenance')
                    if next_maintenance and next_maintenance != 'N/A':
                        try:
                            from app.services.email_service import EmailService
                            next_date = EmailService.parse_date_flexible(next_maintenance).date()
                            days_until = (next_date - today).days
                            
                            if days_until <= 7: upcoming_7_days += 1
                            if days_until <= 14: upcoming_14_days += 1
                            if days_until <= 21: upcoming_21_days += 1
                            if days_until <= 30: upcoming_30_days += 1
                            if days_until <= 60: upcoming_60_days += 1
                            if days_until <= 90: upcoming_90_days += 1
                        except (ValueError, ImportError):
                            pass
                            
            elif status == 'maintained':
                maintained_count += 1
        
        return jsonify({
            'success': True,
            'data': {
                'total_machines': total_machines,
                'ppm_machine_count': len(ppm_data),
                'ocm_machine_count': len(ocm_data),
                'overdue_count': overdue_count,
                'upcoming_count': upcoming_count,
                'maintained_count': maintained_count,
                'upcoming_7_days': upcoming_7_days,
                'upcoming_14_days': upcoming_14_days,
                'upcoming_21_days': upcoming_21_days,
                'upcoming_30_days': upcoming_30_days,
                'upcoming_60_days': upcoming_60_days,
                'upcoming_90_days': upcoming_90_days,
                'current_time': datetime.now().strftime("%A, %d %B %Y — %H:%M:%S")
            }
        })
    except Exception as e:
        logger.error(f"Error refreshing dashboard data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AUDIT LOG ROUTES
# ============================================================================

@views_bp.route('/audit-log')
@login_required
def audit_log_page():
    """Display the audit log page with filtering options."""
    try:
        # Get filter parameters from URL
        event_type_filter = request.args.get('event_type', '')
        user_filter = request.args.get('user', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        search_query = request.args.get('search', '')
        
        # Get all logs initially
        logs = AuditService.get_all_logs()
        
        # Apply filters
        if event_type_filter and event_type_filter != 'all':
            logs = [log for log in logs if log.get('event_type') == event_type_filter]
        
        if user_filter and user_filter != 'all':
            logs = [log for log in logs if log.get('performed_by') == user_filter]
        
        if start_date and end_date:
            logs = AuditService.get_logs_by_date_range(start_date, end_date)
        
        if search_query:
            logs = AuditService.search_logs(search_query)
            
        # Get filter options for dropdowns
        event_types = AuditService.get_event_types()
        users = AuditService.get_unique_users()
        
        # Log the audit log page access
        AuditService.log_event(
            event_type=AuditService.EVENT_TYPES['USER_ACTION'],
            performed_by="User",
            description="Accessed audit log page",
            status=AuditService.STATUS_INFO
        )
        
        return render_template('audit_log.html',
                             logs=logs,
                             event_types=event_types,
                             users=users,
                             current_filters={
                                 'event_type': event_type_filter,
                                 'user': user_filter,
                                 'start_date': start_date,
                                 'end_date': end_date,
                                 'search': search_query
                             })
    except Exception as e:
        logger.error(f"Error loading audit log page: {str(e)}")
        flash('Error loading audit logs.', 'danger')
        return redirect(url_for('views.index'))

@views_bp.route('/audit-log/export')
@login_required
def export_audit_log():
    """Export audit logs to CSV."""
    try:
        # Get filter parameters (same as audit log page)
        event_type_filter = request.args.get('event_type', '')
        user_filter = request.args.get('user', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        search_query = request.args.get('search', '')
        
        # Get filtered logs
        logs = AuditService.get_all_logs()
        
        if event_type_filter and event_type_filter != 'all':
            logs = [log for log in logs if log.get('event_type') == event_type_filter]
        
        if user_filter and user_filter != 'all':
            logs = [log for log in logs if log.get('performed_by') == user_filter]
        
        if start_date and end_date:
            logs = AuditService.get_logs_by_date_range(start_date, end_date)
        
        if search_query:
            logs = AuditService.search_logs(search_query)
        
        # Generate CSV content
        csv_content = "ID,Timestamp,Event Type,Performed By,Description,Status,Details\n"
        
        for log in logs:
            details_str = json.dumps(log.get('details', {})).replace('"', '""')
            csv_content += f"{log.get('id', '')},{log.get('timestamp', '')},{log.get('event_type', '')},{log.get('performed_by', '')},\"{log.get('description', '').replace('\"', '\"\"')}\",{log.get('status', '')},\"{details_str}\"\n"
        
        # Create file-like object
        output = io.StringIO()
        output.write(csv_content)
        output.seek(0)
        
        # Convert to bytes
        output_bytes = io.BytesIO()
        output_bytes.write(output.getvalue().encode('utf-8'))
        output_bytes.seek(0)
        
        # Log the export action
        AuditService.log_event(
            event_type=AuditService.EVENT_TYPES['DATA_EXPORT'],
            performed_by="User",
            description=f"Exported {len(logs)} audit log entries to CSV",
            status=AuditService.STATUS_SUCCESS,
            details={"export_format": "CSV", "record_count": len(logs)}
        )
        
        return send_file(
            output_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'audit_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        logger.error(f"Error exporting audit log: {str(e)}")
        flash('Error exporting audit logs.', 'danger')
        return redirect(url_for('views.audit_log_page'))


# ============================================================================
# BACKUP ROUTES
# ============================================================================

@views_bp.route('/backup/create-full', methods=['POST'])
@login_required
def create_full_backup():
    """Create a full application backup."""
    try:
        from app.services.backup_service import BackupService
        result = BackupService.create_full_backup()
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
            
        return redirect(url_for('views.settings_page'))
        
    except Exception as e:
        logger.error(f"Error creating full backup: {str(e)}")
        flash(f"Error creating full backup: {str(e)}", 'danger')
        return redirect(url_for('views.settings_page'))

@views_bp.route('/backup/create-settings', methods=['POST'])
@login_required
def create_settings_backup():
    """Create a settings-only backup."""
    try:
        from app.services.backup_service import BackupService
        result = BackupService.create_settings_backup()
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
            
        return redirect(url_for('views.settings_page'))
        
    except Exception as e:
        logger.error(f"Error creating settings backup: {str(e)}")
        flash(f"Error creating settings backup: {str(e)}", 'danger')
        return redirect(url_for('views.settings_page'))

@views_bp.route('/backup/list')
@login_required
def list_backups():
    """List all available backups as JSON."""
    try:
        from app.services.backup_service import BackupService
        backups = BackupService.list_backups()
        return jsonify({'success': True, 'backups': backups})
        
    except Exception as e:
        logger.error(f"Error listing backups: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@views_bp.route('/backup/delete/<filename>', methods=['POST'])
@login_required
def delete_backup(filename):
    """Delete a backup file."""
    try:
        from app.services.backup_service import BackupService
        result = BackupService.delete_backup(filename)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
            
        return redirect(url_for('views.settings_page'))
        
    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        flash(f"Error deleting backup: {str(e)}", 'danger')
        return redirect(url_for('views.settings_page'))

@views_bp.route('/backup/download/<backup_type>/<filename>')
@login_required
def download_backup(backup_type, filename):
    """Download a backup file."""
    try:
        from app.services.backup_service import BackupService
        
        if backup_type == 'full':
            backup_path = os.path.join(BackupService.FULL_BACKUPS_DIR, filename)
        elif backup_type == 'settings':
            backup_path = os.path.join(BackupService.SETTINGS_BACKUPS_DIR, filename)
        else:
            flash('Invalid backup type', 'danger')
            return redirect(url_for('views.settings_page'))
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'danger')
            return redirect(url_for('views.settings_page'))
        
        # Log the download action
        AuditService.log_event(
            event_type=AuditService.EVENT_TYPES['DATA_EXPORT'],
            performed_by="User",
            description=f"Downloaded backup file: {filename}",
            status=AuditService.STATUS_SUCCESS,
            details={
                "backup_type": backup_type,
                "filename": filename
            }
        )
        
        return send_file(backup_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Error downloading backup: {str(e)}")
        flash(f"Error downloading backup: {str(e)}", 'danger')
        return redirect(url_for('views.settings_page'))

