import logging
from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

class TrainingRecord(Base):
    __tablename__ = "training_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    department = Column(String)
    trainer = Column(String)
    trained_machines = Column(JSON)  # Storing list of machines as JSON

    def __repr__(self):
        return f"<TrainingRecord(employee_id='{self.employee_id}', name='{self.name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "name": self.name,
            "department": self.department,
            "trainer": self.trainer,
            "trained_machines": self.trained_machines,
        }
