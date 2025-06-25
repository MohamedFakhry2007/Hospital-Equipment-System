"""
User model for handling user authentication and role-based permissions.
"""
from flask_login import UserMixin
from app import db
from app.models.role import Role  # Import Role model
import bcrypt
import logging
from app.utils.logger_setup import setup_logger

logger = logging.getLogger('app')
user_logger = logging.getLogger('app')
user_logger.debug("[app.models.user] Logging started for user.py")

class User(UserMixin, db.Model):
    """Model representing a system user with authentication and role-based permissions."""
    user_logger.debug("[app.models.user] Initializing User model")
    
    __tablename__ = 'users'
    user_logger.debug("[app.models.user] Table name 'users' set")

    id = db.Column(db.Integer, primary_key=True)
    user_logger.debug("[app.models.user] Field 'id' defined as Integer primary key")

    username = db.Column(db.String(80), unique=True, nullable=False)
    user_logger.debug("[app.models.user] Field 'username' defined as String(80), unique and not nullable")

    password_hash = db.Column(db.String(128))
    user_logger.debug("[app.models.user] Field 'password_hash' defined as String(128)")

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)  # Added role_id
    user_logger.debug("[app.models.user] Field 'role_id' defined as Integer foreign key to roles.id")

    # Relationship to Role
    user_logger.debug("[app.models.user] Defining 'role' relationship with Role model")
    role = db.relationship('Role', backref=db.backref('users', lazy=True))
    user_logger.debug("[app.models.user] Relationship 'role' configured with backref")

    def set_password(self, password):
        """Hash and store the user's password."""
        user_logger.info(f"set_password called for user '{self.username}'.")
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user_logger.info(f"Password set for user '{self.username}'.")

    def check_password(self, password):
        user_logger.info(f"[check_password] Stored hash: {self.password_hash!r}")
        user_logger.info(f"[check_password] Input password: {password!r}")
        try:
            result = bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
            user_logger.info(f"Password check {'succeeded' if result else 'failed'} for user '{self.username}'.")
            return result
        except Exception as e:
            user_logger.error(f"Exception during password check: {e}", exc_info=True)
            return False

    def __repr__(self):
        """String representation of the User instance."""
        user_logger.info(f"__repr__ called for user '{self.username}'.")
        return f'<User {self.username}>'

    def has_permission(self, permission_name):
        """Check if the user's role has the specified permission."""
        user_logger.info(f"has_permission called for user '{self.username}' with permission '{permission_name}'.")
        if self.role and self.role.permissions:
            has_perm = any(permission.name == permission_name for permission in self.role.permissions)
            user_logger.info(f"Permission check for user '{self.username}': '{permission_name}' -> {has_perm}")
            return has_perm
        user_logger.warning(f"Permission check for user '{self.username}': '{permission_name}' -> False (no role or permissions)")
        return False