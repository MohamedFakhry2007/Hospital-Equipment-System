"""
Script to fix OCM data migration by directly updating the database with maintenance data.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

def parse_date(date_str):
    """Parse date string in DD/MM/YYYY format to YYYY-MM-DD."""
    if not date_str or str(date_str).upper() in ['N/A', 'NONE', '']:
        return None
    try:
        # Try DD/MM/YYYY format first
        date_obj = datetime.strptime(str(date_str).strip(), '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Try YYYY-MM-DD format
            date_obj = datetime.strptime(str(date_str).strip(), '%Y-%m-%d')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return None

def fix_ocm_migration():
    """Fix OCM data migration by updating maintenance data."""
    # Paths
    db_path = Path('instance/app.db')
    json_path = Path('data/ocm.json')
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return
    if not json_path.exists():
        print(f"Error: JSON file not found at {json_path}")
        return
    
    try:
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        if not json_data:
            print("Error: No data found in JSON file.")
            return
        
        print(f"Loaded {len(json_data)} records from JSON.")
        
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create a mapping of serial to ID for faster lookups
        cursor.execute("SELECT id, serial FROM ocm_equipment")
        serial_to_id = {serial: id_ for id_, serial in cursor.fetchall()}
        
        updated_count = 0
        skipped_count = 0
        
        # Process each record in JSON
        for item in json_data:
            serial = item.get('Serial')
            if not serial:
                print("Skipping record with missing Serial")
                skipped_count += 1
                continue
            
            # Find the record ID
            record_id = serial_to_id.get(serial)
            if not record_id:
                print(f"Skipping record with serial {serial} - not found in database")
                skipped_count += 1
                continue
            
            # Prepare update data
            update_data = {}
            
            # Get values from JSON
            engineer = item.get('Engineer')
            service_date = item.get('Service_Date')
            next_maintenance = item.get('Next_Maintenance')
            status = item.get('Status')
            
            # Add to update data if values exist
            if engineer is not None:
                update_data['engineer'] = str(engineer).strip()
            if service_date is not None:
                update_data['service_date'] = parse_date(service_date)
            if next_maintenance is not None:
                update_data['next_maintenance'] = parse_date(next_maintenance)
            if status is not None:
                update_data['status'] = str(status).strip()
            
            if not update_data:
                skipped_count += 1
                continue
            
            # Build and execute update query
            set_clause = ", ".join(f"{k} = ?" for k in update_data.keys())
            values = list(update_data.values())
            values.append(record_id)  # For WHERE clause
            
            query = f"""
                UPDATE ocm_equipment
                SET {set_clause}
                WHERE id = ?
            """.format(set_clause=set_clause)
            
            try:
                cursor.execute(query, values)
                updated_count += 1
                
                # Commit in batches of 50
                if updated_count % 50 == 0:
                    conn.commit()
                    print(f"Committed {updated_count} updates...")
                    
            except sqlite3.Error as e:
                print(f"Error updating record {record_id} (serial: {serial}): {e}")
                conn.rollback()
        
        # Final commit
        conn.commit()
        
        print("\nUpdate complete!")
        print(f"Records updated: {updated_count}")
        print(f"Records skipped: {skipped_count}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("OCM DATA MIGRATION FIX")
    print("="*80)
    print("This tool will update the maintenance data in the OCM equipment table")
    print("using the information from the ocm.json file.\n")
    
    confirm = input("Do you want to continue? (y/n): ").strip().lower()
    if confirm == 'y':
        fix_ocm_migration()
    else:
        print("Operation cancelled.")
