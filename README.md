# Hospital Equipment Maintenance Management and Reminder System

## Description

This project is a web-based system designed to manage hospital equipment maintenance schedules and send reminders for upcoming maintenance tasks. It provides a way to track equipment, schedule preventive maintenance (PPM), and handle occasional corrective maintenance (OCM). The system is built using Python with the Flask framework.

## Features

*   **Equipment Tracking:**
    *   Add, edit, and delete equipment records.
    *   Support for both Preventive Maintenance (PPM) and Occasional Corrective Maintenance (OCM).
*   **Maintenance Scheduling:**
    *   Define quarterly maintenance schedules for each piece of equipment.
    *   Specify dates and assigned engineers for each maintenance task.
*   **Bulk Import:**
    *   Import equipment and maintenance data from CSV files.
    *   Robust validation of data during import.
    *   Skip duplicated records, showing warnings.
*   **Export:**
    *   Export all PPM data to a CSV file.
*   **Email Reminders:**
    *   Send email reminders for upcoming PPM tasks.
    *   Configurable reminder period (default: 60 days).
*   **Data Storage:**
    *   Data is stored in JSON files (`ppm.json`, `ocm.json`, `training.json`).
* **PPM/OCM data**:
    * PPM data has information about the equipment and it has 4 quarters, with a date and an engineer.
    * OCM data has information about the equipment and it has the OCM for this year and next year and the name of the engineer.
*   **Training Management:**
    *   Track employee training records, including employee details, trainer, machines trained on, and training dates.
    *   Add, edit, and delete training records through a dedicated interface.
    *   Training data is stored in `training.json`.

## Technical Stack

* **Backend:** Python 3.11+ with Flask
* **Database:** MySQL
* **ORM:** SQLAlchemy with Flask-Migrate for database migrations
* **Frontend:** HTML, CSS, JavaScript
* **Package Management:** Poetry
* **Task Scheduling:** APScheduler
* **Data Validation:** Pydantic
* **Data Manipulation:** Pandas

## Prerequisites

1. **Python 3.11+**
   - Download from: https://www.python.org/downloads/
   - During installation, make sure to check "Add Python to PATH"

2. **MySQL Server**
   - Download from: https://dev.mysql.com/downloads/installer/
   - Choose "Developer Default" setup type
   - Remember the root password you set during installation

3. **Git**
   - Download from: https://git-scm.com/downloads

4. **Poetry** (Python package manager)
   - Install using: 
     ```bash
     (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
     ```
   - Restart your terminal after installation

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Hospital-Equipment-System
```

### 2. Set Up MySQL Database

1. Open MySQL Command Line Client
2. Log in as root: 
   ```bash
   mysql -u root -p
   ```
3. Create a new database and user:
   ```sql
   CREATE DATABASE hospital_equipment;
   CREATE USER 'appuser'@'localhost' IDENTIFIED BY 'your_secure_password';
   GRANT ALL PRIVILEGES ON hospital_equipment.* TO 'appuser'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

### 3. Configure Environment Variables
Create a `.env` file in the project root with:
```
FLASK_APP=app.main:create_app
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+mysqlconnector://appuser:your_secure_password@localhost/hospital_equipment
```

### 4. Install Dependencies
```bash
poetry install
```

### 5. Set Up Database Tables
```bash
poetry run flask db init
poetry run flask db migrate -m "Initial tables"
poetry run flask db upgrade
```

### 6. Import Initial Data
If you have SQL dump files:
```bash
mysql -u appuser -p hospital_equipment < database_dump.sql
```

Or if you have JSON data files, use the provided import scripts.

### 7. Start the Development Server
```bash
./devserver.sh
```
The application will be available at: http://localhost:5001

## Development Workflow

### Running Tests
```bash
poetry run pytest
```

### Database Migrations
After making changes to your models:
```bash
poetry run flask db migrate -m "Description of changes"
poetry run flask db upgrade
```

### Adding New Dependencies
```bash
poetry add package-name
```

## Database Management

### Backup Database
```bash
mysqldump -u appuser -p hospital_equipment > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
mysql -u appuser -p hospital_equipment < backup_file.sql
```

## Troubleshooting

### Common Issues

1. **MySQL Connection Issues**
   - Verify MySQL service is running
   - Check credentials in `.env` file
   - Ensure the database and user exist

2. **Python Package Issues**
   ```bash
   poetry install --sync
   ```

3. **Database Migration Problems**
   ```bash
   # Show current migration status
   poetry run flask db current
   
   # If needed, rollback and reapply
   poetry run flask db downgrade
   poetry run flask db upgrade
   ```

## License
[Specify your project's license here]
