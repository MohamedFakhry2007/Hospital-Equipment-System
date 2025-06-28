import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

from app import db
from app.models.training_model import TrainingRecord, TrainingAssignment
from app.constants import DEPARTMENTS, TRAINERS

logger = logging.getLogger(__name__)

def get_departments() -> List[str]:
    """
    Get the list of available departments.
    
    Returns:
        List of department names
    """
    return DEPARTMENTS


def get_trainers() -> List[Dict[str, str]]:
    """
    Get the list of available trainers.
    
    Returns:
        List of trainer dictionaries with id and name
    """
    # Convert list of trainer names to list of dicts with id and name
    return [{'id': str(i+1), 'name': trainer} 
            for i, trainer in enumerate(TRAINERS)]

def load_trainings(
    page: int = 1,
    per_page: int = 20,
    search: str = '',
    department: str = ''
) -> Dict[str, Any]:
    """
    Load paginated training data from the database.
    
    Args:
        page: Page number (1-based)
        per_page: Number of items per page
        search: Search term to filter by name or employee ID
        department: Filter by department
        
    Returns:
        Dict containing items, total count, and pagination info
    """
    try:
        query = TrainingRecord.query
        
        # Apply search filter
        if search:
            search = f'%{search}%'
            query = query.filter(
                or_(
                    TrainingRecord.name.ilike(search),
                    TrainingRecord.employee_id.ilike(search)
                )
            )
            
        # Apply department filter
        if department:
            query = query.filter(TrainingRecord.department == department)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Convert to list of dicts
        items = [record.to_dict() for record in pagination.items]
        
        return {
            'items': items,
            'total': total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'next_page': page + 1 if pagination.has_next else None,
            'prev_page': page - 1 if pagination.has_prev else None
        }
        
    except SQLAlchemyError as e:
        logger.error(f"Database error loading trainings: {str(e)}")
        return {
            'items': [],
            'total': 0,
            'pages': 0,
            'current_page': page,
            'per_page': per_page,
            'has_next': False,
            'has_prev': False,
            'next_page': None,
            'prev_page': None
        }

def save_training(record_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Save a training record to the database.
    
    Args:
        record_data: Dictionary containing training record data
        
    Returns:
        Tuple of (saved_record, error_message)
    """
    try:
        # Handle machine_trainer_assignments
        assignments_data = record_data.pop('machine_trainer_assignments', [])
        
        # Create or update the training record
        if 'id' in record_data and record_data['id']:
            # Update existing record
            record = TrainingRecord.query.get(record_data['id'])
            if not record:
                return None, "Training record not found"
                
            # Update fields
            for key, value in record_data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
        else:
            # Create new record
            record = TrainingRecord.from_dict(record_data)
            db.session.add(record)
        
        # Update assignments
        if assignments_data:
            # Delete existing assignments
            TrainingAssignment.query.filter_by(training_id=record.id).delete()
            
            # Add new assignments
            for assignment_data in assignments_data:
                assignment = TrainingAssignment(
                    training_id=record.id,
                    machine=assignment_data.get('machine', '').strip(),
                    trainer=assignment_data.get('trainer', '').strip(),
                    trained_date=assignment_data.get('trained_date')
                )
                db.session.add(assignment)
        
        db.session.commit()
        
        # Reload the record to get all relationships
        db.session.refresh(record)
        
        return record.to_dict(), ""
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error saving training record: {str(e)}")
        return None, f"Database error: {str(e)}"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving training record: {str(e)}")
        return None, f"Error: {str(e)}"

def get_all_trainings() -> List[Dict[str, Any]]:
    """
    Get all training records (use with caution, prefer load_trainings with pagination).
    
    Returns:
        List of training records as dictionaries
    """
    try:
        records = TrainingRecord.query.all()
        return [record.to_dict() for record in records]
    except SQLAlchemyError as e:
        logger.error(f"Database error getting all trainings: {str(e)}")
        return []

def get_training_by_id(training_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a training record by ID.
    
    Args:
        training_id: ID of the training record to retrieve
        
    Returns:
        Training record as dictionary, or None if not found
    """
    try:
        record = TrainingRecord.query.get(training_id)
        return record.to_dict() if record else None
    except SQLAlchemyError as e:
        logger.error(f"Database error getting training {training_id}: {str(e)}")
        return None

def add_training(training_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Add a new training record.
    
    Args:
        training_data: Dictionary containing training data
        
    Returns:
        Tuple of (created_record, error_message)
    """
    try:
        # Generate a new ID if not provided
        # Ensure machine_trainer_assignments is a list
        if 'machine_trainer_assignments' not in training_data:
            training_data['machine_trainer_assignments'] = []
            
        # Save the training record
        return save_training(training_data)
        
    except Exception as e:
        logger.error(f"Error adding training record: {str(e)}")
        return None, f"Error: {str(e)}"

def update_training(training_id: int, training_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Update an existing training record.
    
    Args:
        training_id: ID of the training record to update
        training_data: Dictionary containing updated training data
        
    Returns:
        Tuple of (updated_record, error_message)
    """
    try:
        # Check if record exists
        record = TrainingRecord.query.get(training_id)
        if not record:
            return None, "Training record not found"
            
        # Set the ID in the data
        training_data['id'] = training_id
        
        # Save the updated record
        return save_training(training_data)
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating training {training_id}: {str(e)}")
        return None, f"Database error: {str(e)}"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating training {training_id}: {str(e)}")
        return None, f"Error: {str(e)}"

def delete_training(training_id: int) -> Tuple[bool, str]:
    """
    Delete a training record by ID.
    
    Args:
        training_id: ID of the training record to delete
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        record = TrainingRecord.query.get(training_id)
        if not record:
            return False, "Training record not found"
            
        # Delete assignments first (due to foreign key constraint)
        TrainingAssignment.query.filter_by(training_id=training_id).delete()
        
        # Delete the record
        db.session.delete(record)
        db.session.commit()
        
        return True, ""
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error deleting training {training_id}: {str(e)}")
        return False, f"Database error: {str(e)}"
    except Exception as e:
        logger.error(f"Error deleting training record {training_id}: {e}")
        return False
