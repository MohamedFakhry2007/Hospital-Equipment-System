# OCM Data Migration to SQLite Database

This document outlines the process of migrating OCM (Other Corrective Maintenance) equipment data from JSON files to an SQLite database, following the same pattern as the PPM (Planned Preventive Maintenance) equipment data.

## Overview

The migration involves:
1. Creating a new database table for OCM equipment
2. Updating the data service layer to use the database instead of JSON files
3. Migrating existing data from JSON to the database
4. Updating all CRUD operations to work with the database

## Database Schema

The OCM equipment data is stored in the `ocm_equipment` table with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| no | Integer | Equipment number |
| department | String(100) | Department name |
| name | String(200) | Equipment name |
| model | String(100) | Equipment model |
| serial | String(100) | Equipment serial number (unique) |
| manufacturer | String(100) | Equipment manufacturer |
| log_number | String(50) | Maintenance log number |
| installation_date | Date | Installation date |
| warranty_end | Date | Warranty end date |
| service_date | Date | Last service date |
| engineer | String(100) | Assigned engineer |
| next_maintenance | Date | Next maintenance date |
| status | String(20) | Maintenance status |
| created_at | DateTime | Record creation timestamp |
| updated_at | DateTime | Record last update timestamp |

## Migration Steps

### 1. Backup Existing Data

Before proceeding with the migration, create a backup of the existing OCM data:

```bash
python migrations/backup_ocm_data.py
```

This will create a timestamped backup in the `data/backups/` directory.

### 2. Run Database Migration

Apply the database migration to create the OCM equipment table:

```bash
flask db upgrade
```

### 3. Migrate Data

Run the data migration script to transfer data from JSON to the database:

```bash
python migrations/migrate_ocm_to_db.py
```

### 4. Verify Migration

After migration, verify that:
1. All records were migrated successfully
2. The data in the database matches the original JSON data
3. The application functions correctly with the new database-backed storage

## Running the Complete Migration

For convenience, you can run the entire migration process with a single command:

```bash
python migrations/run_ocm_migration.py
```

This script will:
1. Create a backup of the existing OCM data
2. Run the database migration
3. Migrate the data from JSON to the database

## Rollback Procedure

If you need to revert the migration:

1. Restore the original JSON file from the backup:
   ```bash
   cp data/backups/ocm_backup_<timestamp>.json data/ocm.json
   ```

2. Rollback the database migration:
   ```bash
   flask db downgrade
   ```

## API Changes

The API endpoints remain the same, but the underlying implementation now uses the database instead of JSON files. The following endpoints are affected:

- `GET /api/equipment/ocm` - Get all OCM equipment
- `GET /api/equipment/ocm/<serial>` - Get OCM equipment by serial
- `POST /api/equipment/ocm` - Add new OCM equipment
- `PUT /api/equipment/ocm/<serial>` - Update OCM equipment
- `DELETE /api/equipment/ocm/<serial>` - Delete OCM equipment

## Testing

After migration, test the following functionality:

1. Viewing all OCM equipment
2. Adding new equipment
3. Updating existing equipment
4. Deleting equipment
5. Searching and filtering equipment
6. Data validation

## Troubleshooting

### Migration Fails

If the migration fails:

1. Check the error message in the console
2. Verify database connection settings in the application configuration
3. Ensure the database user has the necessary permissions
4. Check for duplicate serial numbers in the source data

### Data Issues

If you encounter data issues after migration:

1. Verify the data in the database matches the source JSON
2. Check for any validation errors in the application logs
3. Ensure all required fields are present in the source data

## Maintenance

### Adding New Fields

To add new fields to the OCM equipment table:

1. Create a new database migration:
   ```bash
   flask db migrate -m "add_new_field_to_ocm_equipment"
   ```

2. Edit the generated migration file to add the new column
3. Run the migration:
   ```bash
   flask db upgrade
   ```

### Data Backup

Regularly back up the database to prevent data loss. You can use the following command to create a database backup:

```bash
sqlite3 instance/app.db ".backup 'backup_$(date +%Y%m%d_%H%M%S).db'"
```

## Conclusion

This migration improves the reliability, performance, and maintainability of the OCM equipment data management system by leveraging the power of a relational database. The new implementation follows the same patterns as the existing PPM equipment management system, ensuring consistency across the application.
