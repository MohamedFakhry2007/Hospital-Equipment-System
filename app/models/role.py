"""
Role model for handling user roles and their associated permissions.
"""
import logging
from app import db
from app.models.permission import Permission

logger = logging.getLogger('app')
logger.debug("[app.models.role] Logging started for role.py")

# Association table for the many-to-many relationship between Role and Permission
logger.debug("[app.models.role] Defining association table 'role_permissions'")
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)
logger.debug("[app.models.role] Association table 'role_permissions' defined with foreign keys")


class Role(db.Model):
    """Model representing a user Role with associated permissions."""
    logger.debug("[app.models.role] Initializing Role model")
    
    __tablename__ = 'roles'
    logger.debug("[app.models.role] Table name 'roles' set")

    id = db.Column(db.Integer, primary_key=True)
    logger.debug("[app.models.role] Field 'id' defined as Integer primary key")

    name = db.Column(db.String(80), unique=True, nullable=False)
    logger.debug("[app.models.role] Field 'name' defined as String(80), unique and not nullable")

    # Relationship to Permissions
    logger.debug("[app.models.role] Defining 'permissions' relationship with Permission model")
    permissions = db.relationship(
        'Permission',
        secondary=role_permissions,
        lazy='subquery',  # or 'dynamic' depending on query needs
        backref=db.backref('roles', lazy=True)
    )
    logger.debug("[app.models.role] Relationship 'permissions' configured with backref")

    def __repr__(self):
        logger.debug(f"[app.models.role] Representing Role {self.name}")
        return f'<Role {self.name}>'