from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.sqlite import JSON

class TrainingRecord(db.Model):
    """SQLAlchemy model for training records."""
    __tablename__ = 'training_records'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    last_trained_date = db.Column(db.Date, nullable=True)
    next_due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Store machine-trainer assignments as JSON
    machine_trainer_assignments = db.Column(JSON, nullable=False, default=list)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.name,
            'department': self.department,
            'last_trained_date': self.last_trained_date.isoformat() if self.last_trained_date else None,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'machine_trainer_assignments': self.machine_trainer_assignments,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create model instance from dictionary."""
        return cls(
            employee_id=data.get('employee_id', '').strip(),
            name=data.get('name', '').strip(),
            department=data.get('department', '').strip(),
            last_trained_date=cls._parse_date(data.get('last_trained_date')),
            next_due_date=cls._parse_date(data.get('next_due_date')),
            machine_trainer_assignments=data.get('machine_trainer_assignments', [])
        )
    
    @staticmethod
    def _parse_date(date_str):
        """Parse date string into date object."""
        if not date_str:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            try:
                # Try DD/MM/YYYY format
                return datetime.strptime(date_str, '%d/%m/%Y').date()
            except (ValueError, TypeError):
                return None

class TrainingAssignment(db.Model):
    """SQLAlchemy model for machine-trainer assignments."""
    __tablename__ = 'training_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey('training_records.id'), nullable=False)
    machine = db.Column(db.String(100), nullable=False)
    trainer = db.Column(db.String(100), nullable=False)
    trained_date = db.Column(db.Date, nullable=True)
    
    # Relationship
    training = db.relationship('TrainingRecord', backref='assignments')
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'machine': self.machine,
            'trainer': self.trainer,
            'trained_date': self.trained_date.isoformat() if self.trained_date else None
        }
