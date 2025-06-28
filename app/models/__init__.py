"""
Models package for the application.
"""
from app.models.json_user import JSONUser as User
from app.models.base_model import BaseModel
from app.models.training import Training
from app.models.training_model import TrainingRecord, TrainingAssignment
from app.models.ppm import (
    PPMEntry, 
    PPMEntryCreate, 
    PPMImportEntry, 
    QuarterData
)
from app.models.ocm import (
    OCMEntry,
    OCMEntryCreate
)
from app.models.ppm_equipment import PPMEquipment

# Export the models
__all__ = [
    'User',
    'PPMEquipment', 
    'BaseModel', 
    'Training',
    'PPMEntry',
    'PPMEntryCreate',
    'PPMImportEntry',
    'QuarterData',
    'OCMEntry',
    'OCMEntryCreate'
]
