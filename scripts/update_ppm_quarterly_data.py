"""
Script to update PPM quarterly data in the database.
"""
import sys
import json
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_json_data():
    """Load PPM data from JSON file."""
    json_path = Path('data/ppm.json')
    if not json_path.exists():
        logger.error(f"Error: {json_path} not found.")
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading JSON file: {e}")
        return []

def update_quarterly_data():
    """Update quarterly data in the database from JSON."""
    try:
        from app import create_app
        from app.models.ppm_equipment import PPMEquipment
        from app.extensions import db
        
        logger.info("Creating Flask application...")
        app = create_app()
        
        with app.app_context():
            # Load JSON data
            logger.info("Loading JSON data...")
            json_data = load_json_data()
            if not json_data:
                logger.error("No data found in JSON file.")
                return
                
            logger.info(f"Loaded {len(json_data)} records from JSON.")
            
            # Process each record
            updated_count = 0
            skipped_count = 0
            
            for item in json_data:
                serial = item.get('SERIAL')
                if not serial:
                    logger.warning("Skipping record with missing SERIAL")
                    skipped_count += 1
                    continue
                
                # Find the record in the database
                record = PPMEquipment.query.filter_by(serial=serial).first()
                if not record:
                    logger.warning(f"Record with serial {serial} not found in database")
                    skipped_count += 1
                    continue
                
                # Update quarterly data
                for q in ['I', 'II', 'III', 'IV']:
                    q_key = f'PPM_Q_{q}'
                    if q_key in item and item[q_key]:
                        q_data = item[q_key] or {}
                        
                        # Get values with case-insensitive field names
                        engineer = next(
                            (v for k, v in q_data.items() if k.lower() == 'engineer'),
                            None
                        )
                        quarter_date = next(
                            (v for k, v in q_data.items() 
                             if k.lower() in ['quarter_date', 'quarter date']),
                            None
                        )
                        status = next(
                            (v for k, v in q_data.items() if k.lower() == 'status'),
                            None
                        )
                        
                        # Set the attributes
                        setattr(record, f'ppm_q{q.lower()}_engineer', engineer)
                        setattr(record, f'ppm_q{q.lower()}_status', status)
                        
                        # Parse and set the date
                        if quarter_date and str(quarter_date).strip().upper() not in ['N/A', 'NONE', '']:
                            try:
                                # Try DD/MM/YYYY format first
                                from datetime import datetime
                                date_obj = datetime.strptime(str(quarter_date).strip(), '%d/%m/%Y').date()
                                setattr(record, f'ppm_q{q.lower()}_date', date_obj)
                            except ValueError:
                                try:
                                    # Try YYYY-MM-DD format
                                    date_obj = datetime.strptime(str(quarter_date).strip(), '%Y-%m-%d').date()
                                    setattr(record, f'ppm_q{q.lower()}_date', date_obj)
                                except ValueError:
                                    logger.warning(f"Could not parse date: {quarter_date} for serial {serial}")
                                    setattr(record, f'ppm_q{q.lower()}_date', None)
                        else:
                            setattr(record, f'ppm_q{q.lower()}_date', None)
                
                # Mark as updated
                db.session.add(record)
                updated_count += 1
                
                # Commit in batches of 50
                if updated_count % 50 == 0:
                    db.session.commit()
                    logger.info(f"Committed {updated_count} updates...")
            
            # Final commit for any remaining records
            db.session.commit()
            
            logger.info("\nUpdate complete!")
            logger.info(f"Records updated: {updated_count}")
            logger.info(f"Records skipped: {skipped_count}")
            
    except Exception as e:
        logger.error(f"Error during update: {str(e)}", exc_info=True)
        if 'db' in locals():
            db.session.rollback()
        raise

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PPM QUARTERLY DATA UPDATE TOOL")
    print("="*80)
    print("This tool will update the quarterly maintenance data in the database")
    print("using the information from the ppm.json file.\n")
    
    confirm = input("Do you want to continue? (y/n): ").strip().lower()
    if confirm == 'y':
        update_quarterly_data()
    else:
        print("Operation cancelled.")
