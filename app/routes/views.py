# app/routes/views.py

"""
Frontend routes for rendering HTML pages.
"""
import logging
from dateutil.relativedelta import relativedelta # Keep for now, might be removed if index logic changes enough
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask import send_file
import tempfile
from app.services.data_service import DataService
from datetime import datetime # Keep datetime

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
def index():
    """Display the dashboard with maintenance statistics."""
    
    # Fetch PPM entries
    ppm_data = DataService.get_all_entries(data_type='ppm')
    if isinstance(ppm_data, dict):  # If it's a single dict, wrap in list
        ppm_data = [ppm_data]
    # Add data_type to each PPM entry
    for item in ppm_data:
        item['data_type'] = 'ppm'

    # Fetch OCM entries
    ocm_data = DataService.get_all_entries(data_type='ocm')
    if isinstance(ocm_data, dict):  # If it's a single dict, wrap in list
        ocm_data = [ocm_data]
    # Add data_type to each OCM entry
    for item in ocm_data:
        item['data_type'] = 'ocm'
    

    # Combine both
    all_equipment = ppm_data + ocm_data

    current_date_str = datetime.now().strftime("%A, %d %B %Y - %I:%M:%S %p")
    
    total_machines = len(all_equipment)
    overdue_count = 0
    upcoming_count = 0 # Simplified from upcoming_counts dictionary
    maintained_count = 0
    # The old quarterly_count/yearly_count based on PPM='Yes'/'No' is obsolete.
    # We can count PPM vs OCM types if needed.
    ppm_machine_count = len(ppm_data)
    ocm_machine_count = len(ocm_data)

    for item in all_equipment:
        # Status is now directly available in item['Status']
        status = item.get('Status', 'N/A').lower()
        if status == 'overdue':
            overdue_count += 1
            item['status_class'] = 'danger'
        elif status == 'upcoming':
            upcoming_count += 1
            item['status_class'] = 'warning'
        elif status == 'maintained':
            maintained_count += 1
            item['status_class'] = 'success'
        else:
            item['status_class'] = 'secondary' # For 'N/A' or other statuses

        # 'next_maintenance' display logic
        if item['data_type'] == 'ocm':
             item['display_next_maintenance'] = item.get('Next_Maintenance', 'N/A')
        else: # PPM
             item['display_next_maintenance'] = 'N/A (PPM)'


    return render_template('index.html',
                           current_date=current_date_str,
                           total_machines=total_machines,
                           overdue_count=overdue_count,
                           upcoming_count=upcoming_count, # Pass simplified upcoming_count
                           maintained_count=maintained_count,
                           ppm_machine_count=ppm_machine_count,
                           ocm_machine_count=ocm_machine_count,
                           equipment=all_equipment) # Pass combined list


@views_bp.route('/equipment/<data_type>/list')
def list_equipment(data_type):
    """Display list of equipment (either PPM or OCM)."""
    if data_type not in ('ppm', 'ocm'):
        flash("Invalid equipment type specified.", "warning")
        return redirect(url_for('views.index'))
    try:
        equipment_data = DataService.get_all_entries(data_type)
        for item in equipment_data:
            status = item.get('Status', 'N/A').lower()
            if status == 'overdue':
                item['status_class'] = 'danger'
            elif status == 'upcoming':
                item['status_class'] = 'warning'
            elif status == 'maintained':
                item['status_class'] = 'success'
            else:
                item['status_class'] = 'secondary'
        return render_template('equipment/list.html', equipment=equipment_data, data_type=data_type)
    except Exception as e:
        logger.error(f"Error loading {data_type} list: {str(e)}")
        flash(f"Error loading {data_type.upper()} equipment data.", "danger")
        return render_template('equipment/list.html', equipment=[], data_type=data_type)


@views_bp.route('/equipment/ppm/add', methods=['GET', 'POST'])
def add_ppm_equipment():
    """Handle adding new PPM equipment."""
    if request.method == 'POST':
        form_data = request.form.to_dict()

        ppm_q_i_date_str = form_data.get("PPM_Q_I_date", "").strip()

        q1_date_to_store = ppm_q_i_date_str if ppm_q_i_date_str else None
        q2_date_str = None
        q3_date_str = None
        q4_date_str = None

        if q1_date_to_store:
            q2_date_str = calculate_next_quarter_date(q1_date_to_store, 3)
            if q2_date_str:
                q3_date_str = calculate_next_quarter_date(q2_date_str, 3)
                if q3_date_str:
                    q4_date_str = calculate_next_quarter_date(q3_date_str, 3)

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
            "Status": "Upcoming",  # Default status for new equipment
            "PPM_Q_I": {
                "quarter_date": q1_date_to_store,
                "engineer": form_data.get("PPM_Q_I_engineer", "").strip() or None
            },
            "PPM_Q_II": {
                "quarter_date": q2_date_str,
                "engineer": form_data.get("PPM_Q_II_engineer", "").strip() or None
            },
            "PPM_Q_III": {
                "quarter_date": q3_date_str,
                "engineer": form_data.get("PPM_Q_III_engineer", "").strip() or None
            },
            "PPM_Q_IV": {
                "quarter_date": q4_date_str,
                "engineer": form_data.get("PPM_Q_IV_engineer", "").strip() or None
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
            return render_template('equipment/add_ppm.html', data_type='ppm', form_data=form_data) # Pass original form_data
        except Exception as e:
            logger.error(f"Error adding PPM equipment: {str(e)}")
            flash('An unexpected error occurred while adding.', 'danger')
            return render_template('equipment/add_ppm.html', data_type='ppm', form_data=form_data)

    # GET request: show empty form
    return render_template('equipment/add_ppm.html', data_type='ppm', form_data={})

@views_bp.route('/equipment/ocm/add', methods=['GET', 'POST'])
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
            return render_template('equipment/add_ocm.html', data_type='ocm', form_data=form_data)
        except Exception as e:
            logger.error(f"Error adding OCM equipment: {str(e)}")
            flash('An unexpected error occurred while adding.', 'danger')
            return render_template('equipment/add_ocm.html', data_type='ocm', form_data=form_data)

    return render_template('equipment/add_ocm.html', data_type='ocm', form_data={})


@views_bp.route('/equipment/ppm/edit/<SERIAL>', methods=['GET', 'POST'])
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
            "MANUFACTURER": form_data.get("MANUFACTURER"),            "Department": form_data.get("Department"),
            "LOG_Number": form_data.get("LOG_Number"),
            "Installation_Date": form_data.get("Installation_Date", "").strip() or None,
            "Warranty_End": form_data.get("Warranty_End", "").strip() or None,
            # Eng1-Eng4 removed            "Status": form_data.get("Status", "").strip() or None,
            "PPM_Q_I": {
                "engineer": form_data.get("Q1_Engineer", "").strip() or None,
                "quarter_date": entry.get('PPM_Q_I', {}).get('quarter_date')
            },
            "PPM_Q_II": {
                "engineer": form_data.get("Q2_Engineer", "").strip() or None,
                "quarter_date": entry.get('PPM_Q_II', {}).get('quarter_date')
            },
            "PPM_Q_III": {
                "engineer": form_data.get("Q3_Engineer", "").strip() or None,
                "quarter_date": entry.get('PPM_Q_III', {}).get('quarter_date')
            },
            "PPM_Q_IV": {
                "engineer": form_data.get("Q4_Engineer", "").strip() or None,
                "quarter_date": entry.get('PPM_Q_IV', {}).get('quarter_date')
            },
        }
        if ppm_data_update.get("Name") == "":
            ppm_data_update["Name"] = None

        # Calculate status if not provided or empty in the form
        if not form_data.get("Status"):  # Checks for empty string or None
            # If Status was explicitly set to None by the form processing,
            # remove it before calculation if calculate_status prefers no key.
            # Based on current ppm_data_update construction, Status would be None here.
            if "Status" in ppm_data_update and ppm_data_update["Status"] is None:
                ppm_data_update.pop("Status", None) # Safely pop

            # Ensure all other fields are set in ppm_data_update before this call
            calculated_status = DataService.calculate_status(ppm_data_update, 'ppm')
            ppm_data_update['Status'] = calculated_status
        # If Status *is* provided in the form, it would have been set from:
        # "Status": form_data.get("Status", "").strip() or None,
        # No special handling needed here, it will be used directly.

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
        # and supplement with calculated dates from the original entry for display.
        current_render_data = form_data.copy() # Start with what user submitted
        # Add dates from original entry for display consistency, as they are not submitted by form
        current_render_data['Q1_Date'] = entry.get('PPM_Q_I', {}).get('quarter_date', '')
        current_render_data['Q2_Date'] = entry.get('PPM_Q_II', {}).get('quarter_date', '')
        current_render_data['Q3_Date'] = entry.get('PPM_Q_III', {}).get('quarter_date', '')
        current_render_data['Q4_Date'] = entry.get('PPM_Q_IV', {}).get('quarter_date', '')
        # Ensure other fields from original `entry` that are not in `form_data` are present if needed by template
        for key, value in entry.items():
            if key not in current_render_data:
                 current_render_data[key] = value

        return render_template('equipment/edit_ppm.html', data_type='ppm', entry=current_render_data, SERIAL=SERIAL)

    # GET request: Populate form with existing data
    display_entry = entry.copy()
    # Map PPM_Q_X from loaded entry to QX_Engineer and QX_Date for template
    q_map_to_form = {
        "PPM_Q_I": ("Q1_Date", "Q1_Engineer"),
        "PPM_Q_II": ("Q2_Date", "Q2_Engineer"),
        "PPM_Q_III": ("Q3_Date", "Q3_Engineer"),
        "PPM_Q_IV": ("Q4_Date", "Q4_Engineer"),
    }
    for model_q_key, (form_q_date, form_q_eng) in q_map_to_form.items():
        quarter_data = entry.get(model_q_key, {})
        display_entry[form_q_date] = quarter_data.get('quarter_date', '')
        display_entry[form_q_eng] = quarter_data.get('engineer', '')

    # Remove old Eng fields if they are still in display_entry from old data (though unlikely for new model)
    for i in range(1, 5): display_entry.pop(f'Eng{i}', None)


    return render_template('equipment/edit_ppm.html', data_type='ppm', entry=display_entry, SERIAL=SERIAL)


@views_bp.route('/equipment/ocm/edit/<Serial>', methods=['GET', 'POST'])
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
                return render_template('equipment/edit_ocm.html', data_type='ocm', entry=form_data)
            except Exception as e:
                logger.error(f"Unexpected error updating OCM equipment {Serial}: {str(e)}", exc_info=True)
                flash('An unexpected error occurred while updating.', 'danger')
                return render_template('equipment/edit_ocm.html', data_type='ocm', entry=form_data)

        logger.debug(f"Rendering edit form for OCM equipment {Serial} with data: {entry}")
        return render_template('equipment/edit_ocm.html', data_type='ocm', entry=entry)

    except Exception as e:
        logger.error(f"Critical error in edit_ocm_equipment for Serial {Serial}: {str(e)}", exc_info=True)
        flash('An unexpected error occurred.', 'danger')
        return redirect(url_for('views.list_equipment', data_type='ocm'))


@views_bp.route('/equipment/<data_type>/delete/<path:SERIAL>', methods=['POST'])
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
def import_export_page():
    """Display the import/export page."""
    return render_template('import_export/main.html')

@views_bp.route('/import_equipment', methods=['POST'])
def import_equipment():
    """Import equipment data from CSV file."""
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('views.import_export_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('views.import_export_page'))

    if file and allowed_file(file.filename):
        try:
            logger.info("Starting import_equipment process")
            logger.info(f"Processing file: {file.filename}")

            # Save the file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name

            # Create TextIOWrapper for proper CSV reading
            with open(temp_path, 'r', encoding='utf-8') as f:
                # Read first line to get headers
                headers = f.readline().strip()
                logger.debug(f"CSV Header: {headers}")

                # Get headers as list
                header_list = [h.strip() for h in headers.split(',')]
                logger.debug(f"Header list after splitting and stripping: {header_list}")

                # First try to detect the data type
                logger.debug("Attempting to determine data type from headers")
                from app.services.import_export import ImportExportService
                data_type = ImportExportService.detect_csv_type(header_list)

                if data_type == 'unknown':
                    logger.warning(f"Could not determine data type from headers: {headers}")
                    flash('Invalid CSV format - required columns missing', 'error')
                    return redirect(url_for('views.import_export_page'))

                # Proceed with import using the temporary file path
                success, message, stats = ImportExportService.import_from_csv(data_type, temp_path)
            
            # Clean up temporary file
            import os
            os.unlink(temp_path)
            
            if success:
                flash(f'Import successful: {message}', 'success')
            else:
                flash(f'Import failed: {message}', 'error')
                
            return redirect(url_for('views.import_export_page'))

        except Exception as e:
            logger.error(f"Error during import: {str(e)}")
            flash(f'Error during import: {str(e)}', 'error')
            return redirect(url_for('views.import_export_page'))

    flash('Invalid file type', 'error')
    return redirect(url_for('views.import_export_page'))


@views_bp.route('/export/ppm')
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

@views_bp.route('/settings')
def settings_page():
    """Display the settings page."""
    return render_template('settings.html')