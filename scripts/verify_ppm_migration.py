"""
Script to verify PPM data migration.
"""
import sys
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

def verify_migration():
    """Verify that PPM data was migrated correctly."""
    try:
        from app import create_app
        from app.models.ppm_equipment import PPMEquipment
        
        logger.info("Creating Flask application...")
        app = create_app()
        
        with app.app_context():
            logger.info("Querying PPM equipment records...")
            # Get all records to verify the full dataset
            records = PPMEquipment.query.all()
            
            if not records:
                logger.warning("No PPM records found in the database.")
                return
            
            total_records = len(records)
            logger.info(f"Found {total_records} PPM records in the database.")
            
            # Print summary statistics
            print("\n" + "="*80)
            print("PPM DATA MIGRATION VERIFICATION")
            print("="*80)
            print(f"Total records: {total_records}")
            
            # Check how many records have quarterly data
            q_fields = ['ppm_q1_engineer', 'ppm_q1_date', 'ppm_q1_status',
                      'ppm_q2_engineer', 'ppm_q2_date', 'ppm_q2_status',
                      'ppm_q3_engineer', 'ppm_q3_date', 'ppm_q3_status',
                      'ppm_q4_engineer', 'ppm_q4_date', 'ppm_q4_status']
            
            # Count records with at least one quarterly field populated
            has_q_data = sum(
                1 for record in records 
                if any(getattr(record, field) is not None for field in q_fields)
            )
            
            print(f"\nRecords with quarterly data: {has_q_data} ({has_q_data/total_records:.1%})")
            
            # Show sample records
            print("\n" + "-"*80)
            print("SAMPLE RECORDS:")
            print("-"*80)
            
            for i, record in enumerate(records[:5]):  # Show first 5 records
                print(f"\nRecord {i+1}:")
                print(f"  ID: {record.id}")
                print(f"  Serial: {record.serial}")
                print(f"  Department: {record.department}")
                print(f"  Model: {record.model}")
                
                # Print quarterly data
                for q in ['q1', 'q2', 'q3', 'q4']:
                    engineer = getattr(record, f'ppm_{q}_engineer')
                    q_date = getattr(record, f'ppm_{q}_date')
                    status = getattr(record, f'ppm_{q}_status')
                    
                    if any([engineer, q_date, status]):
                        print(f"  \n  {q.upper()}:")
                        print(f"    Engineer: {engineer}")
                        print(f"    Date: {q_date}")
                        print(f"    Status: {status}")
            
            print("\n" + "="*80)
            print("VERIFICATION COMPLETE")
            print("="*80)
            
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    verify_migration()
