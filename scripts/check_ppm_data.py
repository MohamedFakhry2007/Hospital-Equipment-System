"""
Script to check PPM data in the database.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_data():
    """Check PPM data in the database."""
    try:
        from app import create_app
        from app.models.ppm_equipment import PPMEquipment
        
        print("Creating Flask application...")
        app = create_app()
        
        with app.app_context():
            print("Querying PPM equipment records...")
            
            # Get a few sample records
            records = PPMEquipment.query.limit(5).all()
            
            if not records:
                print("No records found in the database.")
                return
            
            print(f"Found {len(records)} records.")
            
            # Print column names and sample data
            for i, record in enumerate(records):
                print(f"\nRecord {i+1}:")
                print(f"  ID: {record.id}")
                print(f"  Serial: {record.serial}")
                print(f"  Department: {record.department}")
                
                # Print quarterly data
                for q in ['q1', 'q2', 'q3', 'q4']:
                    engineer = getattr(record, f'ppm_{q}_engineer')
                    q_date = getattr(record, f'ppm_{q}_date')
                    status = getattr(record, f'ppm_{q}_status')
                    
                    print(f"  {q.upper()}:")
                    print(f"    Engineer: {engineer}")
                    print(f"    Date: {q_date}")
                    print(f"    Status: {status}")
            
            # Check if we have any records with quarterly data
            has_q_data = PPMEquipment.query.filter(
                (PPMEquipment.ppm_q1_engineer.isnot(None)) |
                (PPMEquipment.ppm_q1_date.isnot(None)) |
                (PPMEquipment.ppm_q1_status.isnot(None)) |
                (PPMEquipment.ppm_q2_engineer.isnot(None)) |
                (PPMEquipment.ppm_q2_date.isnot(None)) |
                (PPMEquipment.ppm_q2_status.isnot(None)) |
                (PPMEquipment.ppm_q3_engineer.isnot(None)) |
                (PPMEquipment.ppm_q3_date.isnot(None)) |
                (PPMEquipment.ppm_q3_status.isnot(None)) |
                (PPMEquipment.ppm_q4_engineer.isnot(None)) |
                (PPMEquipment.ppm_q4_date.isnot(None)) |
                (PPMEquipment.ppm_q4_status.isnot(None))
            ).count()
            
            total = PPMEquipment.query.count()
            print(f"\nTotal records: {total}")
            print(f"Records with quarterly data: {has_q_data} ({has_q_data/total*100:.1f}%)")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PPM DATA CHECK")
    print("="*80)
    check_data()
