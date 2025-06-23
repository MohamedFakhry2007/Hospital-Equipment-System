from flask_login import UserMixin
from app import db
from app.models.role import Role  # Import Role model
import bcrypt

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)  # Added role_id

    # Relationship to Role
    role = db.relationship('Role', backref=db.backref('users', lazy=True))

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def __repr__(self):
        return f'<User {self.username}>'

    def has_permission(self, permission_name):
        """Check if the user's role has a specific permission."""
        if self.role and self.role.permissions:
            return any(permission.name == permission_name for permission in self.role.permissions)
        return False
