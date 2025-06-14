
# app/routes/views.py

"""
Frontend routes for rendering HTML pages.
"""
import logging
from dateutil.relativedelta import relativedelta # Keep for now, might be removed if index logic changes enough
import io
# import csv # Not directly used in views.py after changes, DataService handles CSV logic
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask import send_file # Keep for export
import tempfile # Keep for export
# import pandas as pd # Not directly used in views.py after changes
from app.services.data_service import DataService
from app.services.training_service import TrainingService # Added for Training views
# ValidationService removed

views_bp = Blueprint('views', __name__)
logger = logging.getLogger(__name__)

# Allowed file extension
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            "Installation_Date": form_data.get("Installation_Date"),
            "Warranty_End": form_data.get("Warranty_End"),
            "Eng1": form_data.get("Eng1"),
            "Eng2": form_data.get("Eng2"),
            "Eng3": form_data.get("Eng3"),
            "Eng4": form_data.get("Eng4"),
            "Status": form_data.get("Status") if form_data.get("Status") else None, # Let DataService calculate if empty
            "PPM_Q_I": {"engineer": form_data.get("PPM_Q_I_engineer")},
            "PPM_Q_II": {"engineer": form_data.get("PPM_Q_II_engineer")},
            "PPM_Q_III": {"engineer": form_data.get("PPM_Q_III_engineer")},
            "PPM_Q_IV": {"engineer": form_data.get("PPM_Q_IV_engineer")},
        }
        if not ppm_data["Name"]: # Handle optional Name
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


@views_bp.route('/equipment/ppm/edit/<path:mfg_serial>', methods=['GET', 'POST'])
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
            "Installation_Date": form_data.get("Installation_Date"),
            "Warranty_End": form_data.get("Warranty_End"),
            "Eng1": form_data.get("Eng1"),
            "Eng2": form_data.get("Eng2"),
            "Eng3": form_data.get("Eng3"),
            "Eng4": form_data.get("Eng4"),
            "Status": form_data.get("Status") if form_data.get("Status") else None,
            "PPM_Q_I": {"engineer": form_data.get("PPM_Q_I_engineer")},
            "PPM_Q_II": {"engineer": form_data.get("PPM_Q_II_engineer")},
            "PPM_Q_III": {"engineer": form_data.get("PPM_Q_III_engineer")},
            "PPM_Q_IV": {"engineer": form_data.get("PPM_Q_IV_engineer")},
        }
        if not ppm_data_update["Name"]: ppm_data_update["Name"] = None

        try:
            DataService.update_entry('ppm', mfg_serial, ppm_data_update)
            flash('PPM equipment updated successfully!', 'success')
            return redirect(url_for('views.list_equipment', data_type='ppm'))
        except ValueError as e:
            flash(f"Error updating equipment: {str(e)}", 'danger')
        except KeyError:
             flash(f"Equipment with serial '{mfg_serial}' not found for update.", 'warning')
             return redirect(url_for('views.list_equipment', data_type='ppm'))
        except Exception as e:
            logger.error(f"Error updating PPM equipment {mfg_serial}: {str(e)}")
            flash('An unexpected error occurred during update.', 'danger')
        # Re-render form with current data (entry combined with form_data) and errors
        current_render_data = entry.copy()
        current_render_data.update(form_data)
        for q_key_form, q_field_model in [
            ("PPM_Q_I_engineer", "PPM_Q_I"), ("PPM_Q_II_engineer", "PPM_Q_II"),
            ("PPM_Q_III_engineer", "PPM_Q_III"), ("PPM_Q_IV_engineer", "PPM_Q_IV")
        ]:
            current_render_data[q_field_model] = {"engineer": form_data.get(q_key_form, "")}

        return render_template('equipment/edit_ppm.html', data_type='ppm', entry=current_render_data, mfg_serial=mfg_serial)

    # GET request: Populate form with existing data
    display_entry = entry.copy()
    for q_model, q_form_eng in [("PPM_Q_I", "PPM_Q_I_engineer"), ("PPM_Q_II", "PPM_Q_II_engineer"),
                                ("PPM_Q_III", "PPM_Q_III_engineer"), ("PPM_Q_IV", "PPM_Q_IV_engineer")]:
        display_entry[q_form_eng] = entry.get(q_model, {}).get('engineer', '')

    return render_template('equipment/edit_ppm.html', data_type='ppm', entry=display_entry, mfg_serial=mfg_serial)


@views_bp.route('/equipment/ocm/edit/<path:mfg_serial>', methods=['GET', 'POST'])
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
        except KeyError:
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
            flash(f"{data_type.upper()} equipment '{mfg_serial}' deleted successfully!", 'success')
        else:
            flash(f"{data_type.upper()} equipment '{mfg_serial}' not found.", 'warning')
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
            file_stream = io.TextIOWrapper(file.stream, encoding='utf-8')
            try:
                first_line = file_stream.readline()
                file_stream.seek(0)
                if 'PPM_Q_I' in first_line or 'Eng1' in first_line:
                    data_type_inferred = 'ppm'
                elif 'Next_Maintenance' in first_line or 'Service_Date' in first_line:
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
                for error in result['errors'][:5]:
                    flash(f"- {error}", 'danger')
            elif not msg_parts and not result.get('errors'):
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

# Training Page Views

@views_bp.route('/training', methods=['GET'])
def training_list():
    """Display a list of training records."""
    service = TrainingService()
    try:
        records = service.get_all_training_records()
        # The template 'training/list.html' will be created in a later step.
        return render_template('training/list.html', records=records, title="Training Records")
    except Exception as e:
        current_app.logger.error(f"Error fetching training records for list view: {str(e)}")
        flash("Failed to load training records. Please try again later.", "danger")
        return render_template('training/list.html', records=[], title="Training Records")


@views_bp.route('/training/add', methods=['GET', 'POST'])
def add_training_record_view():
    """Handle adding a new training record."""
    service = TrainingService()
    form_data_for_template = {}

    if request.method == 'POST':
        form_data_for_template = request.form.to_dict()
        try:
            record_data = {
                "employee_id": request.form.get("employee_id", "").strip(),
                "name": request.form.get("name", "").strip(),
                "department": request.form.get("department", "").strip(),
                "trainer": request.form.get("trainer", "").strip(),
                "trained_machines": [m.strip() for m in request.form.get("trained_machines", "").split(',') if m.strip()]
            }

            if not record_data["employee_id"] or not record_data["name"]:
                flash("Employee ID and Name are required.", "warning")
                return render_template('training/add.html', title="Add Training Record", record=form_data_for_template), 400

            service.create_training_record(record_data)
            flash('Training record added successfully!', 'success')
            return redirect(url_for('views.training_list'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('training/add.html', title="Add Training Record", record=form_data_for_template), 400
        except Exception as e:
            current_app.logger.error(f"Error adding training record: {str(e)}")
            flash('Failed to add training record.', 'danger')
            return render_template('training/add.html', title="Add Training Record", record=form_data_for_template), 500

    return render_template('training/add.html', title="Add Training Record", record=form_data_for_template)


@views_bp.route('/training/edit/<int:record_id>', methods=['GET', 'POST'])
def edit_training_record_view(record_id):
    """Handle editing an existing training record."""
    service = TrainingService()

    if request.method == 'POST':
        form_data_for_template = request.form.to_dict()
        form_data_for_template['id'] = record_id
        try:
            record_data = {
                "employee_id": request.form.get("employee_id", "").strip(),
                "name": request.form.get("name", "").strip(),
                "department": request.form.get("department", "").strip(),
                "trainer": request.form.get("trainer", "").strip(),
                "trained_machines": [m.strip() for m in request.form.get("trained_machines", "").split(',') if m.strip()]
            }

            if not record_data["employee_id"] or not record_data["name"]:
                flash("Employee ID and Name are required.", "warning")
                return render_template('training/edit.html', title="Edit Training Record", record=form_data_for_template), 400

            updated_record = service.update_training_record(record_id, record_data)
            if updated_record is None:
                flash('Training record not found or update failed.', 'danger')
                return redirect(url_for('views.training_list'))

            flash('Training record updated successfully!', 'success')
            return redirect(url_for('views.training_list'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('training/edit.html', title="Edit Training Record", record=form_data_for_template), 400
        except Exception as e:
            current_app.logger.error(f"Error updating training record {record_id}: {str(e)}")
            flash('Failed to update training record.', 'danger')
            return render_template('training/edit.html', title="Edit Training Record", record=form_data_for_template), 500

    # GET request
    try:
        record = service.get_training_record(record_id)
        if record:
            # Prepare trained_machines as a comma-separated string for easy display/editing in a text field
            if isinstance(record.get("trained_machines"), list):
                record["trained_machines_str"] = ", ".join(record["trained_machines"])
            else:
                record["trained_machines_str"] = "" # Default if not list or not present
            return render_template('training/edit.html', title="Edit Training Record", record=record)
        else:
            flash('Training record not found.', 'warning')
            return redirect(url_for('views.training_list'))
    except Exception as e:
        current_app.logger.error(f"Error fetching training record {record_id} for edit view: {str(e)}")
        flash("Failed to load record for editing. Please try again later.", "danger")
        return redirect(url_for('views.training_list'))

@views_bp.route('/training/delete/<int:record_id>', methods=['POST'])
def delete_training_record_view(record_id):
    """Handle deleting a training record."""
    service = TrainingService()
    try:
        success = service.delete_training_record(record_id)
        if success:
            flash('Training record deleted successfully!', 'success')
        else:
            flash('Training record not found or could not be deleted.', 'warning')
    except Exception as e:
        current_app.logger.error(f"Error deleting training record {record_id}: {str(e)}")
        flash('Failed to delete training record.', 'danger')
    return redirect(url_for('views.training_list'))
