"""
Script to migrate PPM data from JSON to the database.
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_json_data():
    """Load PPM data from JSON file."""
    json_path = Path('data/ppm.json')
    if not json_path.exists():
        print(f"Error: {json_path} not found.")
        return []
    
    with open(json_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return []

def migrate_data():
    """Migrate data from JSON to database."""
    from app import create_app
    from app.models.ppm_equipment import PPMEquipment
    from app.extensions import db
    
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Check if there's any existing data
        if PPMEquipment.query.first() is not None:
            print("Database already contains PPM data. Migration aborted to prevent duplicates.")
            return
        
        # Load data from JSON
        json_data = load_json_data()
        if not json_data:
            print("No data to migrate.")
            return
        
        print(f"Migrating {len(json_data)} PPM entries to the database...")
        
        # Migrate each entry
        for entry in json_data:
            try:
                # Convert the entry to a PPMEquipment instance
                equipment = PPMEquipment.from_dict(entry)
                db.session.add(equipment)
            except Exception as e:
                print(f"Error migrating entry {entry.get('SERIAL')}: {e}")
                db.session.rollback()
        
        # Commit all changes
        db.session.commit()
        print(f"Successfully migrated {len(json_data)} PPM entries to the database.")

if __name__ == "__main__":
    migrate_data()
