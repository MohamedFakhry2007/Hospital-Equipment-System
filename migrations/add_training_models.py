"""
Migration script to add training models to the database.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from app.extensions import db
from app.models.training_model import TrainingRecord, TrainingAssignment

def run_migration():
    # Create the Flask application
    app = create_app()
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        
        # Verify tables were created
        inspector = db.inspect(db.engine)
        table_names = inspector.get_table_names()
        print(f"\nDatabase tables after migration: {', '.join(table_names) if table_names else 'None'}")
        
        if 'training_record' in table_names:
            print("\nTrainingRecord table created successfully!")
            
            # Check if we have any training records
            count = TrainingRecord.query.count()
            print(f"Found {count} training records in the database.")
            
            if count == 0 and os.path.exists('data/training.json'):
                print("\nImporting training data from JSON file...")
                from migrations.migrate_training_data import migrate_training_data
                migrate_training_data()
                print("Training data import completed.")
                
                # Count records after import
                count_after = TrainingRecord.query.count()
                print(f"Total training records after import: {count_after}")
        else:
            print("\nFailed to create TrainingRecord table.")

if __name__ == "__main__":
    run_migration()
