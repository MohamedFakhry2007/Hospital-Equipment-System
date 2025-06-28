from datetime import datetime
from app.extensions import db

class OCMEquipment(db.Model):
    """SQLAlchemy model for OCM (Other Corrective Maintenance) Equipment."""
    __tablename__ = 'ocm_equipment'
    
    id = db.Column(db.Integer, primary_key=True)
    no = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    serial = db.Column(db.String(100), unique=True, nullable=False, index=True)
    manufacturer = db.Column(db.String(100), nullable=False)
    log_number = db.Column(db.String(50), nullable=False)
    installation_date = db.Column(db.Date)
    warranty_end = db.Column(db.Date)
    service_date = db.Column(db.Date)
    engineer = db.Column(db.String(100))
    next_maintenance = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False)  # Upcoming, Overdue, Maintained
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary matching the Pydantic model structure."""
        def format_date(dt):
            if not dt:
                return ''
            try:
                return dt.strftime('%d/%m/%Y')
            except (AttributeError, ValueError):
                return ''
                
        def safe_str(value):
            """Safely convert value to string, handling None."""
            if value is None:
                return ''
            return str(value).strip()

        return {
            'NO': self.no,
            'Department': safe_str(self.department),
            'Name': safe_str(self.name),
            'Model': safe_str(self.model),
            'Serial': safe_str(self.serial),
            'Manufacturer': safe_str(self.manufacturer),
            'Log_Number': safe_str(self.log_number),
            'Installation_Date': format_date(self.installation_date),
            'Warranty_End': format_date(self.warranty_end),
            'Service_Date': format_date(self.service_date),
            'Engineer': safe_str(self.engineer),
            'Next_Maintenance': format_date(self.next_maintenance),
            'Status': safe_str(self.status)
        }

    @classmethod
    def from_dict(cls, data):
        """Create model instance from dictionary."""
        def parse_date(date_str):
            if not date_str or date_str.upper() == 'N/A':
                return None
            try:
                # Try DD/MM/YYYY format first
                return datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                try:
                    # Fallback to YYYY-MM-DD format
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    return None

        return cls(
            no=int(data.get('NO', 0)),
            department=data.get('Department', '').strip(),
            name=data.get('Name', '').strip(),
            model=data.get('Model', '').strip(),
            serial=data.get('Serial', '').strip(),
            manufacturer=data.get('Manufacturer', '').strip(),
            log_number=data.get('Log_Number', '').strip(),
            installation_date=parse_date(data.get('Installation_Date')),
            warranty_end=parse_date(data.get('Warranty_End')),
            service_date=parse_date(data.get('Service_Date')),
            engineer=data.get('Engineer', '').strip(),
            next_maintenance=parse_date(data.get('Next_Maintenance')),
            status=data.get('Status', 'Upcoming').strip()
        )
        
    def update_from_dict(self, data):
        """Update model instance from dictionary."""
        def parse_date(date_str):
            if not date_str or date_str.upper() == 'N/A':
                return None
            try:
                # Try DD/MM/YYYY format first
                return datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                try:
                    # Fallback to YYYY-MM-DD format
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    return None
                    
        if 'NO' in data:
            self.no = int(data['NO'])
        if 'Department' in data:
            self.department = data['Department'].strip()
        if 'Name' in data:
            self.name = data['Name'].strip()
        if 'Model' in data:
            self.model = data['Model'].strip()
        if 'Serial' in data:
            self.serial = data['Serial'].strip()
        if 'Manufacturer' in data:
            self.manufacturer = data['Manufacturer'].strip()
        if 'Log_Number' in data:
            self.log_number = data['Log_Number'].strip()
        if 'Installation_Date' in data:
            self.installation_date = parse_date(data['Installation_Date'])
        if 'Warranty_End' in data:
            self.warranty_end = parse_date(data['Warranty_End'])
        if 'Service_Date' in data:
            self.service_date = parse_date(data['Service_Date'])
        if 'Engineer' in data:
            self.engineer = data['Engineer'].strip()
        if 'Next_Maintenance' in data:
            self.next_maintenance = parse_date(data['Next_Maintenance'])
        if 'Status' in data:
            self.status = data['Status'].strip()
            
        return self
