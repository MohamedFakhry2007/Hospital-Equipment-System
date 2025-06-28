"""
Script to backup OCM data from the JSON file.

This script creates a timestamped backup of the OCM data before migration.
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
import shutil

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

def backup_ocm_data():
    """Create a backup of the OCM data file."""
    # Define paths
    data_dir = os.path.join(project_root, 'data')
    backup_dir = os.path.join(project_root, 'data', 'backups')
    source_file = os.path.join(data_dir, 'ocm.json')
    
    # Create backups directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Check if source file exists
    if not os.path.exists(source_file):
        print(f"Error: Source file not found: {source_file}")
        return False
    
    try:
        # Create a timestamp for the backup file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"ocm_backup_{timestamp}.json")
        
        # Copy the file
        shutil.copy2(source_file, backup_file)
        
        # Verify the backup was created
        if os.path.exists(backup_file):
            print(f"Backup created successfully: {backup_file}")
            return True
        else:
            print("Error: Failed to create backup file")
            return False
            
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        return False

if __name__ == "__main__":
    print("Creating backup of OCM data...")
    if backup_ocm_data():
        print("Backup completed successfully!")
    else:
        print("Backup failed.")
        sys.exit(1)
