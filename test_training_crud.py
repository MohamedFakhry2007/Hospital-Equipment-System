"""
Test script to verify CRUD operations for training records.
"""
import sys
from datetime import datetime, timedelta
import json

def print_header(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def test_crud_operations():
    from app import create_app
    from app.services.training_service import (
        add_training, get_training_by_id, update_training,
        delete_training, load_trainings
    )
    from app.models.training_model import TrainingRecord
    
    app = create_app()
    
    with app.app_context():
        # Test Data
        test_data = {
            'employee_id': 'TEST001',
            'name': 'Test User',
            'department': 'Testing',
            'last_trained_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'next_due_date': (datetime.now() + timedelta(days=335)).strftime('%Y-%m-%d'),
            'machine_trainer_assignments': [
                {'machine': 'TEST-MACHINE-1', 'trainer': 'Trainer One', 'trained_date': datetime.now().strftime('%Y-%m-%d')},
                {'machine': 'TEST-MACHINE-2', 'trainer': 'Trainer Two', 'trained_date': datetime.now().strftime('%Y-%m-%d')}
            ]
        }
        
        # Test 1: Create a new training record
        print_header("TEST 1: CREATE TRAINING RECORD")
        created, error = add_training(test_data)
        if error:
            print(f"Error creating training record: {error}")
            return
            
        training_id = created['id']
        print(f"Created training record with ID: {training_id}")
        print(json.dumps(created, indent=2))
        
        # Test 2: Retrieve the created record
        print_header("TEST 2: RETRIEVE CREATED RECORD")
        retrieved = get_training_by_id(training_id)
        if retrieved:
            print("Retrieved training record:")
            print(json.dumps(retrieved, indent=2))
        else:
            print("Failed to retrieve created record")
            return
        
        # Test 3: Update the record
        print_header("TEST 3: UPDATE RECORD")
        update_data = {
            'name': 'Updated Test User',
            'department': 'Updated Testing',
            'machine_trainer_assignments': [
                {'machine': 'UPDATED-MACHINE-1', 'trainer': 'Updated Trainer', 'trained_date': datetime.now().strftime('%Y-%m-%d')}
            ]
        }
        updated, error = update_training(training_id, update_data)
        if error:
            print(f"Error updating training record: {error}")
            return
            
        print("Updated training record:")
        print(json.dumps(updated, indent=2))
        
        # Verify the update
        retrieved = get_training_by_id(training_id)
        if retrieved['name'] == 'Updated Test User' and retrieved['department'] == 'Updated Testing':
            print("Update verification: SUCCESS")
        else:
            print("Update verification: FAILED")
        
        # Test 4: List records with pagination
        print_header("TEST 4: LIST RECORDS WITH PAGINATION")
        result = load_trainings(page=1, per_page=5, search='Updated Test User')
        print(f"Total records: {result['total']}")
        print(f"Records on page 1: {len(result['items'])}")
        print("Sample record from list:")
        if result['items']:
            print(json.dumps(result['items'][0], indent=2))
        
        # Test 5: Delete the test record
        print_header("TEST 5: DELETE RECORD")
        success, error = delete_training(training_id)
        if success:
            print(f"Successfully deleted training record {training_id}")
            
            # Verify deletion
            deleted = get_training_by_id(training_id)
            if deleted is None:
                print("Deletion verification: SUCCESS (record not found)")
            else:
                print("Deletion verification: FAILED (record still exists)")
        else:
            print(f"Failed to delete training record: {error}")
        
        # Test 6: Verify database operations
        print_header("TEST 6: VERIFY DATABASE OPERATIONS")
        with app.app_context():
            # Check if the record exists in the database
            record = TrainingRecord.query.get(training_id)
            if record is None:
                print("Database verification: Record not found (expected after deletion)")
            else:
                print("Database verification: Record still exists in database")
                
            # Check assignments were also deleted
            from app.models.training_model import TrainingAssignment
            assignments = TrainingAssignment.query.filter_by(training_id=training_id).all()
            print(f"Found {len(assignments)} assignments for deleted record (expected 0)")

if __name__ == "__main__":
    test_crud_operations()
