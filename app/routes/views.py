# app/routes/views.py

"""
Frontend routes for rendering HTML pages.
"""
import logging
import io
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask import send_file
import tempfile
import pandas as pd
from app.services.data_service import DataService
from app.services.validation import ValidationService

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
    from datetime import datetime, timedelta
    
    data = DataService.get_all_entries('ppm')
    current_date = datetime.now().strftime("%A, %d %B %Y - %I:%M:%S %p")
    
    # Calculate statistics
    total_machines = len(data)
    overdue_count = 0
    upcoming_counts = {7: 0, 14: 0, 21: 0, 30: 0, 60: 0, 90: 0}
    quarterly_count = sum(1 for item in data if item.get('PPM') == 'Yes')
    yearly_count = total_machines - quarterly_count
    
    # Process equipment data for display
    for item in data:
        next_maintenance = None
        # Find next maintenance date from quarters
        for q in ['I', 'II', 'III', 'IV']:
            q_date = item.get(f'PPM_Q_{q}', {}).get('date')
            if q_date:
                date = datetime.strptime(q_date, '%d/%m/%Y')
                if date > datetime.now():
                    next_maintenance = date
                    break
        
        if next_maintenance:
            days_until = (next_maintenance - datetime.now()).days
            if days_until < 0:
                overdue_count += 1
            else:
                for day_limit in upcoming_counts.keys():
                    if days_until <= day_limit:
                        upcoming_counts[day_limit] += 1
        
        # Add status information to items
        if next_maintenance:
            days_until = (next_maintenance - datetime.now()).days
            if days_until < 0:
                item['status'] = 'Overdue'
                item['status_class'] = 'danger'
            elif days_until <= 7:
                item['status'] = 'Due Soon'
                item['status_class'] = 'warning'
            else:
                item['status'] = 'OK'
                item['status_class'] = 'success'
            item['next_maintenance'] = next_maintenance.strftime('%d/%m/%Y')
        else:
            item['status'] = 'No Schedule'
            item['status_class'] = 'secondary'
            item['next_maintenance'] = 'Not Scheduled'

    return render_template('index.html',
                         current_date=current_date,
                         total_machines=total_machines,
                         overdue_count=overdue_count,
                         upcoming_counts=upcoming_counts,
                         quarterly_count=quarterly_count,
                         yearly_count=yearly_count,
                         equipment=data)


@views_bp.route('/equipment/<data_type>/list')
def list_equipment(data_type):
    """Display list of equipment (either PPM or OCM)."""
    if data_type not in ('ppm', 'ocm'):
        flash("Invalid equipment type specified.", "warning")
        return redirect(url_for('views.index'))
    try:
        data = DataService.get_all_entries(data_type)
        # Render the list template which now includes add/import buttons
        return render_template('equipment/list.html', equipment=data, data_type=data_type)
    except Exception as e:
        logger.error(f"Error loading {data_type} list: {str(e)}")
        flash(f"Error loading {data_type.upper()} equipment data.", "danger")
        return render_template('equipment/list.html', equipment=[], data_type=data_type)


@views_bp.route('/equipment/ppm/add', methods=['GET', 'POST'])
def add_ppm_equipment():
    """Handle adding new PPM equipment."""
    if request.method == 'POST':
        form_data = request.form.to_dict()
        is_valid, errors = ValidationService.validate_ppm_form(form_data) # Using existing validation

        if is_valid:
            try:
                model_data = ValidationService.convert_ppm_form_to_model(form_data) # Using existing conversion
                DataService.add_entry('ppm', model_data)
                flash('PPM equipment added successfully!', 'success')
                return redirect(url_for('views.list_equipment', data_type='ppm'))
            except ValueError as e: # Handles duplicate MFG_SERIAL from DataService
                flash(f"Error adding equipment: {str(e)}", 'danger')
            except Exception as e:
                logger.error(f"Error adding PPM equipment: {str(e)}")
                flash('An unexpected error occurred while adding.', 'danger')
        else:
            flash('Please correct the errors below.', 'warning')
            # Re-render add form with errors and submitted data
            return render_template('equipment/add.html', data_type='ppm', errors=errors, form_data=form_data)

    # GET request: show empty form
    return render_template('equipment/add.html', data_type='ppm', errors={}, form_data={})


@views_bp.route('/equipment/ppm/edit/<mfg_serial>', methods=['GET', 'POST'])
def edit_ppm_equipment(mfg_serial):
    """Handle editing existing PPM equipment."""
    entry = DataService.get_entry('ppm', mfg_serial)
    if not entry:
        flash(f"Equipment with serial '{mfg_serial}' not found.", 'warning')
        return redirect(url_for('views.list_equipment', data_type='ppm'))

    if request.method == 'POST':
        form_data = request.form.to_dict()
        # Validate the submitted form data (excluding MFG_SERIAL change check)
        is_valid, errors = ValidationService.validate_ppm_form(form_data)

        if is_valid:
            try:
                 # Explicitly check if MFG_SERIAL was changed in form
                if form_data.get('MFG_SERIAL') != mfg_serial:
                     raise ValueError("Cannot change MFG_SERIAL during edit.")

                model_data = ValidationService.convert_ppm_form_to_model(form_data)
                DataService.update_entry('ppm', mfg_serial, model_data)
                flash('PPM equipment updated successfully!', 'success')
                return redirect(url_for('views.list_equipment', data_type='ppm'))
            except ValueError as e: # Handles MFG_SERIAL change attempt or DataService validation error
                flash(f"Error updating equipment: {str(e)}", 'danger')
            except KeyError: # Should not happen if entry check passed, but good practice
                 flash(f"Equipment with serial '{mfg_serial}' not found for update.", 'warning')
                 return redirect(url_for('views.list_equipment', data_type='ppm'))
            except Exception as e:
                logger.error(f"Error updating PPM equipment {mfg_serial}: {str(e)}")
                flash('An unexpected error occurred during update.', 'danger')
        else: # Validation failed
            flash('Please correct the errors below.', 'warning')
            # Re-render edit form with errors and the submitted data
            # Combine original entry data with form data for display
            current_data = entry.copy()
            current_data.update(form_data)
             # Reformat quarter data from potentially submitted values
            for q in ['I', 'II', 'III', 'IV']:
                 current_data[f'PPM_Q_{q}_date'] = form_data.get(f'PPM_Q_{q}_date', '')
                 current_data[f'PPM_Q_{q}_engineer'] = form_data.get(f'PPM_Q_{q}_engineer', '')
            return render_template('equipment/edit.html', data_type='ppm', entry=current_data, errors=errors, mfg_serial=mfg_serial)

    # GET request: Populate form with existing data
    form_data_display = entry.copy()
     # Reformat quarter data from stored structure for template display
    for q in ['I', 'II', 'III', 'IV']:
         q_data = entry.get(f'PPM_Q_{q}', {})
         form_data_display[f'PPM_Q_{q}_date'] = q_data.get('date', '')
         form_data_display[f'PPM_Q_{q}_engineer'] = q_data.get('engineer', '')

    return render_template('equipment/edit.html', data_type='ppm', entry=form_data_display, errors={}, mfg_serial=mfg_serial)


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
            try:
                reader = csv.reader(file_stream)
                header = next(reader)
                file_stream.seek(0) # Reset stream position for pandas
            except (StopIteration, csv.Error) as e:
                 flash(f'Error reading CSV header: {e}', 'danger')
                 return redirect(url_for('views.import_export_page'))


            # Infer data_type based on header columns (adjust logic as needed)
            if 'PPM Q I' in header or 'Q1_ENGINEER' in header: # Check for PPM specific columns
                data_type = 'ppm'
            elif 'OCM' in header and 'ENGINEER' in header: # Check for OCM specific columns
                data_type = 'ocm'
            else:
                # Default or raise error if type cannot be inferred
                flash('Could not determine data type (PPM/OCM) from CSV header.', 'warning')
                return redirect(url_for('views.import_export_page'))


            # Call DataService to handle the import logic
            result = DataService.import_data(data_type, file_stream)

            # Process results and flash messages
            if result['added_count'] > 0:
                flash(f"Successfully imported {result['added_count']} {data_type.upper()} records.", 'success')
            if result['skipped_count'] > 0:
                flash(f"Skipped {result['skipped_count']} records due to duplicates or validation errors. Check logs for details.", 'warning')
            if not result['errors'] and result['added_count'] == 0 and result['skipped_count'] == 0:
                 flash("No new records were added. The file might be empty or contain only existing records.", "info")
            # Optionally show specific errors if needed, but keep it concise for the user
            # for error in result['errors'][:3]: # Show first few errors
            #    flash(f"Import issue: {error}", "danger")

            return redirect(url_for('views.list_equipment', data_type=data_type))

        except Exception as e:
            logger.exception("Error during file import process.") # Log full traceback
            flash(f'An unexpected error occurred during import: {str(e)}', 'danger')
            return redirect(url_for('views.import_export_page'))
    else:
        flash('Invalid file type. Only CSV files are allowed.', 'warning')
        return redirect(url_for('views.import_export_page'))


@views_bp.route('/export/ppm')
def export_equipment():
    """
    Export PPM equipment data to CSV for download."""
    data_type = 'ppm'
    try:
        # Call DataService to handle the export logic for PPM

        csv_content = DataService.export_data(data_type='ppm')

         # Create temporary file for download
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmpfile:
            tmpfile.write(csv_content)
            tmp_file_path = tmpfile.name

        # Drop 'NO' column from output (auto-generated on import)
        # Create temporary file for download
        # Send file to client
        return send_file(
            tmp_file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name='ppm_export.csv'
        )

    except Exception as e:
        logger.exception(f"Error exporting {data_type} data: {str(e)}")
        flash(f"An error occurred during export: {str(e)}", 'danger')
        return redirect(url_for('views.import_export_page'))