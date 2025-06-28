"""
Script to migrate OCM data from JSON files to the database.

This script reads the existing OCM data from the JSON file and migrates it to the database.
"""
import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from app import create_app, db
from app.models.ocm_equipment import OCMEquipment
from app.services.ocm_service import OCMService

# Create the Flask application context
app = create_app()
app.app_context().push()

def migrate_ocm_data():
    """Migrate OCM data from JSON file to the database."""
    # Get the path to the OCM JSON file
    json_path = os.path.join(project_root, 'data', 'ocm.json')
    
    # Check if the file exists
    if not os.path.exists(json_path):
        print(f"Error: OCM JSON file not found at {json_path}")
        return False
    
    try:
        # Read the JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            ocm_data = json.load(f)
        
        if not isinstance(ocm_data, list):
            print("Error: OCM data is not a list")
            return False
        
        print(f"Found {len(ocm_data)} OCM records to migrate")
        
        # Process each entry
        success_count = 0
        error_count = 0
        
        for entry in ocm_data:
            try:
                def parse_date(date_str):
                    """Helper to parse date strings into date objects"""
                    if not date_str or date_str == 'N/A':
                        return None
                    try:
                        # Try to parse the date in DD/MM/YYYY format
                        return datetime.strptime(date_str, '%d/%m/%Y').date()
                    except (ValueError, TypeError):
                        return None
                
                def parse_date(date_str):
                    """Parse date string to date object or return None"""
                    if not date_str or date_str == 'N/A':
                        return None
                    try:
                        # Try to parse the date in DD/MM/YYYY format
                        return datetime.strptime(date_str, '%d/%m/%Y').date()
                    except (ValueError, TypeError):
                        try:
                            # Try YYYY-MM-DD format as fallback
                            return datetime.strptime(date_str, '%Y-%m-%d').date()
                        except (ValueError, TypeError):
                            return None
                
                # Parse dates to date objects first
                installation_date = parse_date(entry.get('Installation_Date'))
                warranty_end = parse_date(entry.get('Warranty_End'))
                service_date = parse_date(entry.get('Service_Date'))
                next_maintenance = parse_date(entry.get('Next_Maintenance'))
                
                # Format dates as strings for the Pydantic model
                def format_date_for_model(date_obj):
                    if date_obj is None:
                        return 'N/A'
                    return date_obj.strftime('%d/%m/%Y')
                
                # Get or generate required fields
                serial = entry.get('Serial')
                if not serial or not str(serial).strip():
                    serial = f"GEN-{uuid.uuid4().hex[:8]}"
                    
                log_number = entry.get('Log_Number')
                if not log_number or not str(log_number).strip():
                    log_number = f"LOG-{uuid.uuid4().hex[:8]}"
                
                # Create the mapped entry with date strings for the Pydantic model
                # Ensure name is never None - use EQUIPMENT field or 'Unnamed Equipment' as fallback
                name = (entry.get('Name') or entry.get('EQUIPMENT') or 'Unnamed Equipment').strip()
                if not name or name.upper() == 'N/A':
                    name = f"{entry.get('Model', 'Equipment')} - {entry.get('SERIAL', 'No Serial')}"
                
                mapped_entry = {
                    'NO': int(entry.get('NO', 0)),
                    'Department': entry.get('Department', 'N/A').strip(),
                    'Name': name,
                    'Model': entry.get('Model', 'N/A').strip(),
                    'SERIAL': serial.strip(),
                    'MANUFACTURER': entry.get('Manufacturer', 'N/A').strip(),
                    'LOG_NO': log_number.strip(),
                    'Installation_Date': format_date_for_model(installation_date),
                    'Warranty_End': format_date_for_model(warranty_end),
                    'Service_Date': format_date_for_model(service_date),
                    'ENGINEER': entry.get('Engineer', 'Technician').strip(),
                    'Next_Maintenance': format_date_for_model(next_maintenance),
                    'Status': entry.get('Status', 'Upcoming').strip(),
                    'PPM': entry.get('PPM', '')  # Add PPM field
                }
                
                # Debug: Print the mapped entry being processed
                print(f"\nProcessing entry: {mapped_entry.get('SERIAL')}")
                print(f"Installation_Date: {mapped_entry.get('Installation_Date')}")
                print(f"Warranty_End: {mapped_entry.get('Warranty_End')}")
                print(f"Service_Date: {mapped_entry.get('Service_Date')}")
                print(f"Next_Maintenance: {mapped_entry.get('Next_Maintenance')}")
                
                # Add the entry using the OCMService
                try:
                    result, error = OCMService.add_equipment(mapped_entry)
                    
                    if error:
                        print(f"Error adding entry {mapped_entry.get('SERIAL')}: {error}")
                        error_count += 1
                    else:
                        success_count += 1
                        print(f"Successfully added entry: {mapped_entry.get('SERIAL')}")
                        if success_count % 10 == 0:  # Print progress more frequently
                            print(f"Progress: {success_count} records migrated, {error_count} errors")
                except Exception as e:
                    print(f"Unexpected error adding entry {mapped_entry.get('SERIAL')}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    error_count += 1
                        
            except Exception as e:
                print(f"Error processing entry: {str(e)}")
                error_count += 1
        
        print(f"Migration complete. Success: {success_count}, Errors: {error_count}")
        return True
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting OCM data migration...")
    if migrate_ocm_data():
        print("Migration completed successfully!")
    else:
        print("Migration failed.")
        sys.exit(1)
