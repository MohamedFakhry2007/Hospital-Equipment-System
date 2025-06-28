"""
Migration script to import training data from JSON to database.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from app import create_app, db
from app.models.training_model import TrainingRecord, TrainingAssignment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_date(date_str):
    """Parse date string into date object."""
    if not date_str:
        return None
    try:
        # Try ISO format first
        return datetime.fromisoformat(date_str).date()
    except (ValueError, TypeError):
        try:
            # Try DD/MM/YYYY format
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            return None

def migrate_training_data():
    """Migrate training data from JSON file to database."""
    app = create_app()
    
    with app.app_context():
        # Check if the tables exist, create them if not
        db.create_all()
        
        # Path to the training data JSON file
        json_path = Path('data/training.json')
        
        if not json_path.exists():
            logger.error(f"Training data file not found: {json_path}")
            return
        
        try:
            # Read the JSON data
            with open(json_path, 'r', encoding='utf-8') as f:
                training_data = json.load(f)
            
            if not isinstance(training_data, list):
                logger.error("Invalid training data format: expected a list of records")
                return
            
            total_records = len(training_data)
            logger.info(f"Found {total_records} training records to migrate")
            
            migrated_count = 0
            skipped_count = 0
            
            for record in training_data:
                try:
                    # Check if record with this ID already exists
                    existing = TrainingRecord.query.get(record.get('id'))
                    if existing:
                        logger.debug(f"Skipping existing record with ID {record.get('id')}")
                        skipped_count += 1
                        continue
                    
                    # Create a new training record
                    training_record = TrainingRecord(
                        id=record.get('id'),
                        employee_id=record.get('employee_id', '').strip(),
                        name=record.get('name', '').strip(),
                        department=record.get('department', '').strip(),
                        last_trained_date=parse_date(record.get('last_trained_date')),
                        next_due_date=parse_date(record.get('next_due_date')),
                        machine_trainer_assignments=record.get('machine_trainer_assignments', [])
                    )
                    
                    db.session.add(training_record)
                    
                    # Add machine-trainer assignments
                    assignments = record.get('machine_trainer_assignments', [])
                    for assignment in assignments:
                        if not assignment.get('machine') or not assignment.get('trainer'):
                            continue
                            
                        training_assignment = TrainingAssignment(
                            training_id=training_record.id,
                            machine=assignment['machine'].strip(),
                            trainer=assignment['trainer'].strip(),
                            trained_date=parse_date(assignment.get('trained_date'))
                        )
                        db.session.add(training_assignment)
                    
                    db.session.commit()
                    migrated_count += 1
                    
                    if migrated_count % 10 == 0:
                        logger.info(f"Migrated {migrated_count}/{total_records} records...")
                        
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error migrating record {record.get('id')}: {str(e)}")
                    skipped_count += 1
            
            logger.info(f"Migration completed. Success: {migrated_count}, Skipped: {skipped_count}")
            
        except Exception as e:
            logger.error(f"Error during migration: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    migrate_training_data()
