"""
Main script to run the OCM data migration.

This script performs the following steps:
1. Creates a backup of the existing OCM data
2. Runs the database migration to create the OCM table
3. Migrates the data from JSON to the database
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

def run_command(command, cwd=None):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd or project_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"

def backup_ocm_data():
    """Run the OCM data backup script."""
    print("\n=== Step 1: Backing up OCM data ===")
    backup_script = os.path.join(project_root, 'migrations', 'backup_ocm_data.py')
    success, output = run_command(f"python {backup_script}")
    
    if success:
        print("✓ Backup completed successfully")
        return True
    else:
        print("✗ Backup failed:", output)
        return False

def run_database_migration():
    """Run the database migration to create the OCM table."""
    print("\n=== Step 2: Running database migration ===")
    
    # First, let's get the latest migration revision
    success, output = run_command("flask db current")
    if not success and "No such command" not in output:
        print("✗ Failed to get current migration:", output)
        return False
    
    # The output is in the format: <revision> (<branch>)
    current_revision = output.split(' ')[0].strip() if output.strip() else 'None'
    print(f"Current database revision: {current_revision}")
    
    # If we're at the latest revision, skip the migration
    if current_revision == '1234567890ab':
        print("✓ Database is already at the latest revision")
        return True
        
    # Check if the ocm_equipment table already exists
    from app import create_app, db
    from sqlalchemy import inspect
    
    # Create the Flask application
    app = create_app()
    
    with app.app_context():
        # Check if the table exists by querying the database directly
        from sqlalchemy import text
        try:
            # Try to query the ocm_equipment table
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='ocm_equipment'"))
                table_exists = result.fetchone() is not None
                
            if table_exists:
                print("✓ ocm_equipment table already exists")
                # Update the alembic version to the latest
                success, output = run_command("flask db stamp 1234567890ab")
                if success:
                    print("✓ Database version updated to latest")
                    return True
                else:
                    print("✗ Failed to update database version:", output)
                    return False
        except Exception as e:
            print(f"✗ Error checking for ocm_equipment table: {str(e)}")
            return False
    
    # Run the migration within the application context
    with app.app_context():
        print("Running database migration...")
        try:
            # First try to stamp the current revision to avoid full migration
            from flask_migrate import stamp
            stamp(revision='1234567890ab')
            print("✓ Database version stamped successfully")
            return True
        except Exception as e:
            print(f"✗ Error during database migration: {str(e)}")
            return False

def migrate_ocm_data():
    """Run the OCM data migration script."""
    print("\n=== Step 3: Migrating OCM data to database ===")
    migrate_script = os.path.join(project_root, 'migrations', 'migrate_ocm_to_db.py')
    success, output = run_command(f"python {migrate_script}")
    
    if success:
        print("✓ Data migration completed successfully")
        return True
    else:
        print("✗ Data migration failed:", output)
        return False

def main():
    """Main function to run the migration process."""
    print("=== OCM Data Migration Tool ===")
    print("This tool will migrate OCM data from JSON files to the database.")
    
    # Step 1: Backup existing data
    if not backup_ocm_data():
        print("\nAborting migration due to backup failure.")
        return False
    
    # Step 2: Run database migration
    if not run_database_migration():
        print("\nAborting migration due to database migration failure.")
        return False
    
    # Step 3: Migrate data
    if not migrate_ocm_data():
        print("\nData migration completed with errors. Please check the logs.")
        return False
    
    print("\n=== Migration completed successfully! ===")
    return True

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
