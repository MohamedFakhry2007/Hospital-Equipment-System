"""
Permission model for handling user permissions in the system.
"""
import logging
from app import db

logger = logging.getLogger('app')
logger.debug("[app.models.permission] Logging started for permission.py")

class Permission(db.Model):
    """Model representing a Permission in the database."""
    logger.debug("[app.models.permission] Initializing Permission model")
    
    __tablename__ = 'permissions'
    logger.debug("[app.models.permission] Table name 'permissions' set")

    id = db.Column(db.Integer, primary_key=True)
    logger.debug("[app.models.permission] Field 'id' defined as Integer primary key")

    name = db.Column(db.String(255), unique=True, nullable=False)
    logger.debug("[app.models.permission] Field 'name' defined as String(255), unique and not nullable")

    def __repr__(self):
        logger.debug(f"[app.models.permission] Representing Permission {self.name}")
        return f'<Permission {self.name}>'