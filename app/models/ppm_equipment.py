from datetime import datetime
from app.extensions import db

class PPMEquipment(db.Model):
    """SQLAlchemy model for PPM Equipment."""
    __tablename__ = 'ppm_equipment'
    
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200))
    model = db.Column(db.String(100), nullable=False)
    serial = db.Column(db.String(100), unique=True, nullable=False, index=True)
    manufacturer = db.Column(db.String(100), nullable=False)
    log_number = db.Column(db.String(50), nullable=False)
    installation_date = db.Column(db.Date)
    warranty_end = db.Column(db.Date)
    status = db.Column(db.String(50))
    
    # Quarterly maintenance data
    ppm_q1_engineer = db.Column(db.String(100))
    ppm_q1_date = db.Column(db.Date)
    ppm_q1_status = db.Column(db.String(50))
    
    ppm_q2_engineer = db.Column(db.String(100))
    ppm_q2_date = db.Column(db.Date)
    ppm_q2_status = db.Column(db.String(50))
    
    ppm_q3_engineer = db.Column(db.String(100))
    ppm_q3_date = db.Column(db.Date)
    ppm_q3_status = db.Column(db.String(50))
    
    ppm_q4_engineer = db.Column(db.String(100))
    ppm_q4_date = db.Column(db.Date)
    ppm_q4_status = db.Column(db.String(50))
    
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
            'NO': self.id,
            'Department': safe_str(self.department),
            'Name': safe_str(self.name) if self.name is not None else '',
            'MODEL': safe_str(self.model) if self.model is not None else '',
            'SERIAL': safe_str(self.serial) if self.serial is not None else '',
            'MANUFACTURER': safe_str(self.manufacturer) if self.manufacturer is not None else '',
            'LOG_Number': safe_str(self.log_number) if self.log_number is not None else '',
            'Installation_Date': format_date(self.installation_date),
            'Warranty_End': format_date(self.warranty_end),
            'PPM_Q_I': {
                'engineer': safe_str(self.ppm_q1_engineer) if self.ppm_q1_engineer is not None else '',
                'quarter_date': format_date(self.ppm_q1_date),
                'status': safe_str(self.ppm_q1_status) if self.ppm_q1_status is not None else ''
            },
            'PPM_Q_II': {
                'engineer': safe_str(self.ppm_q2_engineer) if self.ppm_q2_engineer is not None else '',
                'quarter_date': format_date(self.ppm_q2_date),
                'status': safe_str(self.ppm_q2_status) if self.ppm_q2_status is not None else ''
            },
            'PPM_Q_III': {
                'engineer': safe_str(self.ppm_q3_engineer) if self.ppm_q3_engineer is not None else '',
                'quarter_date': format_date(self.ppm_q3_date),
                'status': safe_str(self.ppm_q3_status) if self.ppm_q3_status is not None else ''
            },
            'PPM_Q_IV': {
                'engineer': safe_str(self.ppm_q4_engineer) if self.ppm_q4_engineer is not None else '',
                'quarter_date': format_date(self.ppm_q4_date),
                'status': safe_str(self.ppm_q4_status) if self.ppm_q4_status is not None else ''
            },
            'Status': safe_str(self.status) if self.status is not None else ''
        }

    @classmethod
    def from_dict(cls, data):
        """Create model instance from dictionary."""
        def parse_date(date_str):
            if not date_str or str(date_str).upper() in ['N/A', 'NONE', '']:
                return None
            try:
                return datetime.strptime(str(date_str).strip(), '%d/%m/%Y').date()
            except (ValueError, TypeError) as e:
                try:
                    # Try to parse different date formats if the first one fails
                    if isinstance(date_str, str) and '-' in date_str:
                        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
                    return None
                except (ValueError, TypeError):
                    return None

        equipment = cls(
            department=data.get('Department', ''),
            name=data.get('Name'),
            model=data.get('MODEL', ''),
            serial=data.get('SERIAL', ''),
            manufacturer=data.get('MANUFACTURER', ''),
            log_number=data.get('LOG_Number', ''),
            installation_date=parse_date(data.get('Installation_Date')),
            warranty_end=parse_date(data.get('Warranty_End')),
            status=data.get('Status')
        )

        # Set quarterly data - handle both upper and lower case field names
        for q in ['I', 'II', 'III', 'IV']:
            q_key = f'PPM_Q_{q}'
            if q_key in data and data[q_key]:
                q_data = data[q_key] or {}
                # Handle case-insensitive field names
                engineer = next((v for k, v in q_data.items() if k.lower() == 'engineer'), None)
                quarter_date = next((v for k, v in q_data.items() if k.lower() in ['quarter_date', 'quarter date']), None)
                status = next((v for k, v in q_data.items() if k.lower() == 'status'), None)
                
                setattr(equipment, f'ppm_q{q.lower()}_engineer', engineer)
                setattr(equipment, f'ppm_q{q.lower()}_date', parse_date(quarter_date))
                setattr(equipment, f'ppm_q{q.lower()}_status', status)

        return equipment
