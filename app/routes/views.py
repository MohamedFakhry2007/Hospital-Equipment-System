# app/routes/views.py

"""
Frontend routes for rendering HTML pages.
"""
import logging
from dateutil.relativedelta import relativedelta # Keep for now, might be removed if index logic changes enough
import io
# import csv # Not directly used in views.py after changes, DataService handles CSV logic
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask import send_file # Keep for export
import tempfile # Keep for export
# import pandas as pd # Not directly used in views.py after changes
from app.services.data_service import DataService
# ValidationService removed

views_bp = Blueprint('views', __name__)
logger = logging.getLogger(__name__)

# Allowed file extension
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@views_bp.route('/')
def index():
    """Display the dashboard with maintenance statistics."""
    from datetime import datetime # Keep datetime
    
    # Fetch both PPM and OCM data to show a combined overview or select one
    ppm_data = DataService.get_all_entries('ppm')
    for item in ppm_data: item['data_type'] = 'ppm'
    ocm_data = DataService.get_all_entries('ocm')
    for item in ocm_data: item['data_type'] = 'ocm'
    all_equipment = ppm_data + ocm_data # Combine for simplicity or process separately

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
        # Structure data for PPMEntry model
        # PPM_Q_X fields expect {"engineer": "name"}
        ppm_data = {
            "EQUIPMENT": form_data.get("EQUIPMENT"),
            "MODEL": form_data.get("MODEL"),
            "Name": form_data.get("Name"), # Optional
            "MFG_SERIAL": form_data.get("MFG_SERIAL"),
            "MANUFACTURER": form_data.get("MANUFACTURER"),
            "Department": form_data.get("Department"),
            "LOG_NO": form_data.get("LOG_NO"),
            "Installation_Date": form_data.get("Installation_Date", "").strip() or None,
            "Warranty_End": form_data.get("Warranty_End", "").strip() or None,
            # Eng1-Eng4 removed
            "Status": form_data.get("Status", "").strip() or None, # Let DataService calculate if empty or None
            "PPM_Q_I": {"engineer": form_data.get("Q1_Engineer", "").strip() or None},
            "PPM_Q_II": {"engineer": form_data.get("Q2_Engineer", "").strip() or None},
            "PPM_Q_III": {"engineer": form_data.get("Q3_Engineer", "").strip() or None},
            "PPM_Q_IV": {"engineer": form_data.get("Q4_Engineer", "").strip() or None},
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
            "EQUIPMENT": form_data.get("EQUIPMENT"),
            "MODEL": form_data.get("MODEL"),
            "Name": form_data.get("Name"), # Optional
            "MFG_SERIAL": form_data.get("MFG_SERIAL"),
            "MANUFACTURER": form_data.get("MANUFACTURER"),
            "Department": form_data.get("Department"),
            "LOG_NO": form_data.get("LOG_NO"),
            "Installation_Date": form_data.get("Installation_Date"),
            "Warranty_End": form_data.get("Warranty_End"),
            "Service_Date": form_data.get("Service_Date"),
            "Next_Maintenance": form_data.get("Next_Maintenance"),
            "ENGINEER": form_data.get("ENGINEER"),
            "Status": form_data.get("Status") if form_data.get("Status") else None, # Let DataService calculate
            "PPM": form_data.get("PPM", "") # Optional field from OCM model
        }
        if not ocm_data["Name"]: # Handle optional Name
            ocm_data["Name"] = None

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


@views_bp.route('/equipment/ppm/edit/<mfg_serial>', methods=['GET', 'POST'])
def edit_ppm_equipment(mfg_serial):
    """Handle editing existing PPM equipment."""
    entry = DataService.get_entry('ppm', mfg_serial)
    if not entry:
        flash(f"PPM Equipment with serial '{mfg_serial}' not found.", 'warning')
        return redirect(url_for('views.list_equipment', data_type='ppm'))

    if request.method == 'POST':
        form_data = request.form.to_dict()
        ppm_data_update = {
            "EQUIPMENT": form_data.get("EQUIPMENT"),
            "MODEL": form_data.get("MODEL"),
            "Name": form_data.get("Name"),
            "MFG_SERIAL": mfg_serial, # Should not change
            "MANUFACTURER": form_data.get("MANUFACTURER"),
            "Department": form_data.get("Department"),
            "LOG_NO": form_data.get("LOG_NO"),
            "Installation_Date": form_data.get("Installation_Date", "").strip() or None,
            "Warranty_End": form_data.get("Warranty_End", "").strip() or None,
            # Eng1-Eng4 removed
            "Status": form_data.get("Status", "").strip() or None,
            "PPM_Q_I": {"engineer": form_data.get("Q1_Engineer", "").strip() or None},
            "PPM_Q_II": {"engineer": form_data.get("Q2_Engineer", "").strip() or None},
            "PPM_Q_III": {"engineer": form_data.get("Q3_Engineer", "").strip() or None},
            "PPM_Q_IV": {"engineer": form_data.get("Q4_Engineer", "").strip() or None},
        }
        if ppm_data_update.get("Name") == "":
            ppm_data_update["Name"] = None

        try:
            DataService.update_entry('ppm', mfg_serial, ppm_data_update)
            flash('PPM equipment updated successfully!', 'success')
            return redirect(url_for('views.list_equipment', data_type='ppm'))
        except ValueError as e:
            flash(f"Error updating equipment: {str(e)}", 'danger')
        except KeyError: # Should not typically be raised by DataService.update_entry for not found.
             flash(f"Equipment with serial '{mfg_serial}' not found for update.", 'warning')
             return redirect(url_for('views.list_equipment', data_type='ppm'))
        except Exception as e:
            logger.error(f"Error updating PPM equipment {mfg_serial}: {str(e)}")
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

        return render_template('equipment/edit_ppm.html', data_type='ppm', entry=current_render_data, mfg_serial=mfg_serial)

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


    return render_template('equipment/edit_ppm.html', data_type='ppm', entry=display_entry, mfg_serial=mfg_serial)


@views_bp.route('/equipment/ocm/edit/<mfg_serial>', methods=['GET', 'POST'])
def edit_ocm_equipment(mfg_serial):
    """Handle editing existing OCM equipment."""
    entry = DataService.get_entry('ocm', mfg_serial)
    if not entry:
        flash(f"OCM Equipment with serial '{mfg_serial}' not found.", 'warning')
        return redirect(url_for('views.list_equipment', data_type='ocm'))

    if request.method == 'POST':
        form_data = request.form.to_dict()
        ocm_data_update = {
            "EQUIPMENT": form_data.get("EQUIPMENT"),
            "MODEL": form_data.get("MODEL"),
            "Name": form_data.get("Name"),
            "MFG_SERIAL": mfg_serial, # Should not change
            "MANUFACTURER": form_data.get("MANUFACTURER"),
            "Department": form_data.get("Department"),
            "LOG_NO": form_data.get("LOG_NO"),
            "Installation_Date": form_data.get("Installation_Date"),
            "Warranty_End": form_data.get("Warranty_End"),
            "Service_Date": form_data.get("Service_Date"),
            "Next_Maintenance": form_data.get("Next_Maintenance"),
            "ENGINEER": form_data.get("ENGINEER"),
            "Status": form_data.get("Status") if form_data.get("Status") else None,
            "PPM": form_data.get("PPM", "")
        }
        if not ocm_data_update["Name"]: ocm_data_update["Name"] = None

        try:
            DataService.update_entry('ocm', mfg_serial, ocm_data_update)
            flash('OCM equipment updated successfully!', 'success')
            return redirect(url_for('views.list_equipment', data_type='ocm'))
        except ValueError as e:
            flash(f"Error updating equipment: {str(e)}", 'danger')
        except KeyError: # Should not happen
             flash(f"Equipment with serial '{mfg_serial}' not found for update.", 'warning')
             return redirect(url_for('views.list_equipment', data_type='ocm'))
        except Exception as e:
            logger.error(f"Error updating OCM equipment {mfg_serial}: {str(e)}")
            flash('An unexpected error occurred during update.', 'danger')

        current_render_data = entry.copy()
        current_render_data.update(form_data)
        return render_template('equipment/edit_ocm.html', data_type='ocm', entry=current_render_data, mfg_serial=mfg_serial)

    return render_template('equipment/edit_ocm.html', data_type='ocm', entry=entry, mfg_serial=mfg_serial)


@views_bp.route('/equipment/<data_type>/delete/<path:mfg_serial>', methods=['POST'])
def delete_equipment(data_type, mfg_serial):
    """Handle deleting existing equipment."""
    if data_type not in ('ppm', 'ocm'):
        flash("Invalid equipment type specified.", "warning")
        return redirect(url_for('views.index'))

    try:
        deleted = DataService.delete_entry(data_type, mfg_serial)
        if deleted:
            flash(f'{data_type.upper()} equipment \'{mfg_serial}\' deleted successfully!', 'success')
        else:
            flash(f'{data_type.upper()} equipment \'{mfg_serial}\' not found.', 'warning')
    except Exception as e:
        logger.error(f"Error deleting {data_type} equipment {mfg_serial}: {str(e)}")
        flash('An unexpected error occurred during deletion.', 'danger')

    return redirect(url_for('views.list_equipment', data_type=data_type))

# --- Import/Export Routes ---

@views_bp.route('/import-export')
def import_export_page():
    """Display the import/export page."""
    return render_template('import_export/main.html')

@views_bp.route('/import', methods=['POST'])
def import_equipment():
    """Handle CSV file upload for bulk import."""
    if 'file' not in request.files:
        flash('No file part selected.', 'warning')
        return redirect(url_for('views.import_export_page'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'warning')
        return redirect(url_for('views.import_export_page'))

    if file and allowed_file(file.filename):
        try:
            # Use TextIOWrapper for consistent text handling
            file_stream = io.TextIOWrapper(file.stream, encoding='utf-8')

            # Determine data_type from header before passing to DataService
            # Read header safely
            # Read header safely to infer data_type
            # This part of logic remains, but using file_stream directly
            # We need to be careful with consuming the stream before pandas uses it.
            # One way is to read a line, then reset.
            try:
                # Peek at the header to infer data_type
                first_line = file_stream.readline()
                file_stream.seek(0) # Reset stream for DataService.import_data

                # Basic inference (can be made more robust)
                # This is a simplified version of header check.
                # DataService.import_data will use pandas which handles CSV parsing robustly.
                # Updated to check for new PPM specific headers like Q1_Engineer, Q2_Engineer etc.
                if 'Q1_Engineer' in first_line or \
                   'Q2_Engineer' in first_line or \
                   'Q3_Engineer' in first_line or \
                   'Q4_Engineer' in first_line: # New PPM specific fields
                    data_type_inferred = 'ppm'
                elif 'Next_Maintenance' in first_line or \
                     'Service_Date' in first_line: # OCM specific fields
                    data_type_inferred = 'ocm'
                else:
                    flash('Could not reliably determine data type (PPM/OCM) from CSV header.', 'warning')
                    return redirect(url_for('views.import_export_page'))
            except Exception as header_read_error:
                logger.error(f"Failed to read CSV header for type inference: {header_read_error}")
                flash(f'Error reading CSV header: {header_read_error}', 'danger')
                return redirect(url_for('views.import_export_page'))


            result = DataService.import_data(data_type_inferred, file_stream)

            msg_parts = []
            if result.get('added_count', 0) > 0:
                msg_parts.append(f"{result['added_count']} new records added.")
            if result.get('updated_count', 0) > 0:
                msg_parts.append(f"{result['updated_count']} records updated.")
            if result.get('skipped_count', 0) > 0:
                msg_parts.append(f"{result['skipped_count']} records skipped.")

            final_message = " ".join(msg_parts) if msg_parts else "No changes made from the import."

            if result.get('errors'):
                flash(f"Import completed with issues. {final_message}", 'warning')
                for error in result['errors'][:5]: # Show up to 5 specific errors
                    flash(f"- {error}", 'danger')
            elif not msg_parts and not result.get('errors'): # No adds, no updates, no skips, no errors
                 flash("The imported file did not result in any changes.", "info")
            else:
                flash(f"Import successful. {final_message}", 'success')

            return redirect(url_for('views.list_equipment', data_type=data_type_inferred))

        except Exception as e:
            logger.exception("Error during file import process.")
            flash(f'An unexpected error occurred during import: {str(e)}', 'danger')
            return redirect(url_for('views.import_export_page'))
    else:
        flash('Invalid file type. Only CSV files are allowed.', 'warning')
        return redirect(url_for('views.import_export_page'))


@views_bp.route('/export/ppm')
def export_equipment_ppm():
    """Export PPM equipment data to CSV."""
    try:
        csv_content = DataService.export_data(data_type='ppm')
        # Use BytesIO for in-memory file handling with send_file
        mem_file = io.BytesIO()
        mem_file.write(csv_content.encode('utf-8'))
        mem_file.seek(0)
        return send_file(
            mem_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name='ppm_export.csv'
        )
    except Exception as e:
        logger.exception("Error exporting PPM data.")
        flash(f"An error occurred during PPM export: {str(e)}", 'danger')
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