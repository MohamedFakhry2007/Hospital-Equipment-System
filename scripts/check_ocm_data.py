"""
Script to check OCM data in the database.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_ocm_data():
    """Check OCM data in the database."""
    try:
        from app import create_app
        from app.models.ocm_equipment import OCMEquipment
        
        print("Creating Flask application...")
        app = create_app()
        
        with app.app_context():
            print("Querying OCM equipment records...")
            
            # Get a few sample records
            records = OCMEquipment.query.limit(5).all()
            
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
                print(f"  Engineer: {record.engineer}")
                print(f"  Service Date: {record.service_date}")
                print(f"  Next Maintenance: {record.next_maintenance}")
                print(f"  Status: {record.status}")
            
            # Check if we have any records with maintenance data
            has_maintenance_data = OCMEquipment.query.filter(
                (OCMEquipment.engineer.isnot(None)) |
                (OCMEquipment.service_date.isnot(None)) |
                (OCMEquipment.next_maintenance.isnot(None)) |
                (OCMEquipment.status.isnot(None))
            ).count()
            
            total = OCMEquipment.query.count()
            print(f"\nTotal records: {total}")
            print(f"Records with maintenance data: {has_maintenance_data} ({has_maintenance_data/max(1, total)*100:.1f}%)")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    print("\n" + "="*80)
    print("OCM DATA CHECK")
    print("="*80)
    check_ocm_data()
