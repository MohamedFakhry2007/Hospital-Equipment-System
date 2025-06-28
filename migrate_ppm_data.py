"""
Script to migrate PPM data from JSON file to SQL database.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models.ppm_equipment import PPMEquipment

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('migration.log')
        ]
    )
    return logging.getLogger(__name__)

def load_json_data(file_path):
    """Load PPM data from JSON file."""
    logger = logging.getLogger(__name__)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return []

def migrate_ppm_data():
    """Migrate PPM data from JSON to SQL database."""
    logger = setup_logging()
    logger.info("Starting PPM data migration...")
    
    # Create app and push context
    app = create_app()
    
    with app.app_context():
        # Check if we already have data in the database
        existing_count = PPMEquipment.query.count()
        if existing_count > 0:
            logger.warning(f"Found {existing_count} existing PPM records in the database.")
            response = input("Do you want to continue and add to existing data? (y/n): ")
            if response.lower() != 'y':
                logger.info("Migration cancelled by user.")
                return
        
        # Load data from JSON file
        json_file = Path('data/ppm.json')
        if not json_file.exists():
            logger.error(f"PPM JSON file not found at: {json_file}")
            return
            
        ppm_data = load_json_data(json_file)
        if not ppm_data:
            logger.error("No data found in PPM JSON file or file is empty.")
            return
            
        logger.info(f"Found {len(ppm_data)} records in PPM JSON file.")
        
        # Track migration stats
        success_count = 0
        error_count = 0
        
        # Process each record
        for record in ppm_data:
            try:
                # Check if record with this serial already exists
                if PPMEquipment.query.filter_by(serial=record.get('SERIAL')).first():
                    logger.warning(f"Skipping duplicate record with SERIAL: {record.get('SERIAL')}")
                    error_count += 1
                    continue
                
                # Create PPMEquipment instance from record
                equipment = PPMEquipment.from_dict(record)
                db.session.add(equipment)
                success_count += 1
                
                # Commit in batches of 50
                if success_count % 50 == 0:
                    db.session.commit()
                    logger.info(f"Committed {success_count} records so far...")
                    
            except Exception as e:
                db.session.rollback()
                error_count += 1
                logger.error(f"Error processing record {record.get('SERIAL')}: {str(e)}")
        
        # Final commit for any remaining records
        try:
            db.session.commit()
            logger.info(f"Migration completed. Success: {success_count}, Errors: {error_count}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during final commit: {str(e)}")
            logger.info(f"Migration partially completed. Success: {success_count}, Errors: {error_count + 1}")

if __name__ == "__main__":
    migrate_ppm_data()
