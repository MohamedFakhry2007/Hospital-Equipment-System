from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from app.services.training_service import (
    load_trainings, get_training_by_id, add_training,
    update_training, delete_training, get_departments, get_trainers
)

# Create blueprint
training_bp = Blueprint('training', __name__, url_prefix='/training')

@training_bp.route('/', methods=['GET'])
@login_required
def list_trainings():
    """Render the training list page with pagination."""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        department = request.args.get('department', '')
        
        # Get paginated training data
        data = load_trainings(
            page=page,
            per_page=per_page,
            search=search,
            department=department
        )
        
        # Get departments for filter dropdown
        departments = get_departments()
        
        return render_template(
            'training/list.html',
            trainings=data['items'],
            pagination={
                'total': data['total'],
                'page': page,
                'per_page': per_page,
                'pages': data['pages'],
                'has_next': data['has_next'],
                'has_prev': data['has_prev'],
                'next_page': data['next_page'],
                'prev_page': data['prev_page'],
            },
            search=search,
            departments=departments,
            selected_department=department
        )
    except Exception as e:
        flash(f'Error loading training records: {str(e)}', 'error')
        return render_template('training/list.html', trainings=[], pagination=None)

@training_bp.route('/<int:training_id>', methods=['GET'])
@login_required
def view_training(training_id):
    """View a single training record."""
    try:
        training = get_training_by_id(training_id)
        if not training:
            flash('Training record not found', 'error')
            return redirect(url_for('training.list_trainings'))
            
        return render_template('training/view.html', training=training)
    except Exception as e:
        flash(f'Error viewing training record: {str(e)}', 'error')
        return redirect(url_for('training.list_trainings'))

@training_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_training():
    """Create a new training record."""
    if request.method == 'GET':
        # Get available trainers for the form
        trainers = get_trainers()
        departments = get_departments()
        return render_template('training/form.html', trainers=trainers, departments=departments)
    
    try:
        # Get form data
        form_data = request.form.to_dict()
        
        # Handle machine-trainer assignments
        assignments = []
        if 'machine' in request.form and 'trainer' in request.form:
            machines = request.form.getlist('machine')
            trainers = request.form.getlist('trainer')
            trained_dates = request.form.getlist('trained_date')
            
            for i, machine in enumerate(machines):
                if machine and i < len(trainers):
                    assignment = {
                        'machine': machine,
                        'trainer': trainers[i],
                        'trained_date': trained_dates[i] if i < len(trained_dates) else None
                    }
                    assignments.append(assignment)
        
        form_data['machine_trainer_assignments'] = assignments
        
        # Add the training record
        training, error = add_training(form_data)
        if error:
            flash(f'Error creating training record: {error}', 'error')
            return redirect(url_for('training.create_training'))
            
        flash('Training record created successfully', 'success')
        return redirect(url_for('training.view_training', training_id=training['id']))
    except Exception as e:
        flash(f'Error creating training record: {str(e)}', 'error')
        return redirect(url_for('training.create_training'))

@training_bp.route('/<int:training_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_training(training_id):
    """Edit an existing training record."""
    if request.method == 'GET':
        try:
            training = get_training_by_id(training_id)
            if not training:
                flash('Training record not found', 'error')
                return redirect(url_for('training.list_trainings'))
                
            trainers = get_trainers()
            departments = get_departments()
            return render_template(
                'training/form.html',
                training=training,
                trainers=trainers,
                departments=departments,
                is_edit=True
            )
        except Exception as e:
            flash(f'Error loading training record: {str(e)}', 'error')
            return redirect(url_for('training.list_trainings'))
    
    try:
        # Get form data
        form_data = request.form.to_dict()
        form_data['id'] = training_id
        
        # Handle machine-trainer assignments
        assignments = []
        if 'machine' in request.form and 'trainer' in request.form:
            machines = request.form.getlist('machine')
            trainers = request.form.getlist('trainer')
            trained_dates = request.form.getlist('trained_date')
            
            for i, machine in enumerate(machines):
                if machine and i < len(trainers):
                    assignment = {
                        'machine': machine,
                        'trainer': trainers[i],
                        'trained_date': trained_dates[i] if i < len(trained_dates) and trained_dates[i] else None
                    }
                    assignments.append(assignment)
        
        form_data['machine_trainer_assignments'] = assignments
        
        # Update the training record
        training, error = update_training(training_id, form_data)
        if error:
            flash(f'Error updating training record: {error}', 'error')
            return redirect(url_for('training.edit_training', training_id=training_id))
            
        flash('Training record updated successfully', 'success')
        return redirect(url_for('training.view_training', training_id=training_id))
    except Exception as e:
        flash(f'Error updating training record: {str(e)}', 'error')
        return redirect(url_for('training.edit_training', training_id=training_id))

@training_bp.route('/<int:training_id>/delete', methods=['POST'])
@login_required
def delete_training_route(training_id):
    """Delete a training record."""
    try:
        success, error = delete_training(training_id)
        if not success:
            flash(f'Error deleting training record: {error}', 'error')
        else:
            flash('Training record deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting training record: {str(e)}', 'error')
    
    return redirect(url_for('training.list_trainings'))

# API Endpoints
@training_bp.route('/api/trainings', methods=['GET'])
@login_required
def api_list_trainings():
    """API endpoint to get paginated training data."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        department = request.args.get('department', '')
        
        data = load_trainings(
            page=page,
            per_page=per_page,
            search=search,
            department=department
        )
        
        return jsonify({
            'success': True,
            'data': data['items'],
            'pagination': {
                'total': data['total'],
                'pages': data['pages'],
                'page': page,
                'per_page': per_page,
                'has_next': data['has_next'],
                'has_prev': data['has_prev']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
