from app import db
from app.models.permission import Permission

# Association table for the many-to-many relationship between Role and Permission
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    # Relationship to Permissions
    permissions = db.relationship(
        'Permission',
        secondary=role_permissions,
        lazy='subquery', # or 'dynamic' depending on query needs
        backref=db.backref('roles', lazy=True)
    )

    def __repr__(self):
        return f'<Role {self.name}>'
