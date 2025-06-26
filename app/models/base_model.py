"""
Base model for all models in the application.
"""
from flask_login import UserMixin
import logging

logger = logging.getLogger('app')

class BaseModel:
    """Base model class that provides common functionality."""
    
    @classmethod
    def get_by_id(cls, id):
        """Get an instance by ID."""
        raise NotImplementedError("Subclasses must implement get_by_id")
    
    @classmethod
    def get_all(cls):
        """Get all instances."""
        raise NotImplementedError("Subclasses must implement get_all")
