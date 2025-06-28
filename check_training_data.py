"""Script to verify training data in the database."""
import json
from datetime import datetime
from sqlalchemy import text

def check_training_data():
    from app import create_app
    from app.extensions import db
    from app.models.training_model import TrainingRecord, TrainingAssignment
    
    app = create_app()
    with app.app_context():
        try:
            # Count total training records
            total_records = TrainingRecord.query.count()
            print(f"\nTotal training records in database: {total_records}")
            
            if total_records > 0:
                # Get a sample record
                sample = TrainingRecord.query.first()
                print("\nSample training record:")
                print(f"ID: {sample.id}")
                print(f"Title: {sample.title}")
                print(f"Department: {sample.department}")
                print(f"Status: {sample.status}")
                print(f"Start Date: {sample.start_date}")
                print(f"End Date: {sample.end_date}")
                print(f"Machine-Trainer Assignments: {sample.machine_trainer_assignments}")
                
                # Count assignments
                assignments = TrainingAssignment.query.count()
                print(f"\nTotal training assignments: {assignments}")
                
                # Get unique departments
                departments = db.session.query(TrainingRecord.department).distinct().all()
                departments = [d[0] for d in departments if d[0]]
                print(f"\nUnique departments: {', '.join(departments) if departments else 'None'}")
                
                # Get record counts by status
                status_counts = db.session.query(
                    TrainingRecord.status,
                    db.func.count(TrainingRecord.id)
                ).group_by(TrainingRecord.status).all()
                
                print("\nRecord counts by status:")
                for status, count in status_counts:
                    print(f"  {status}: {count}")
                    
            else:
                print("\nNo training records found in the database.")
                
                # Check if JSON file exists
                import os
                json_path = os.path.join('data', 'training.json')
                if os.path.exists(json_path):
                    print(f"\nTraining JSON file found at: {json_path}")
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                        print(f"Found {len(data)} records in JSON file.")
                        
                        # Check if we should import the data
                        import sys
                        if '--import' in sys.argv:
                            print("\nRunning import...")
                            from migrations.migrate_training_data import migrate_training_data
                            migrate_training_data()
                            print("Import completed. Run this script again to verify the data.")
                        else:
                            print("\nTo import this data, run this script with the --import flag.")
                
        except Exception as e:
            print(f"\nError checking training data: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_training_data()
