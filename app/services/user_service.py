from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User, Role, Permission

def create_user(username, password, role_name, is_active=True):
    """Create a new user with the given credentials and role."""
    if User.query.filter_by(username=username).first():
        raise ValueError('Username already exists')
    
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        raise ValueError(f'Role {role_name} does not exist')
    
    user = User(
        username=username,
        role=role_name,
        is_active=is_active
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    return user

def update_user(user_id, **kwargs):
    """Update user attributes."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError('User not found')
    
    if 'username' in kwargs and kwargs['username'] != user.username:
        if User.query.filter_by(username=kwargs['username']).first():
            raise ValueError('Username already exists')
        user.username = kwargs['username']
    
    if 'password' in kwargs:
        user.set_password(kwargs['password'])
    
    if 'role' in kwargs:
        role = Role.query.filter_by(name=kwargs['role']).first()
        if not role:
            raise ValueError('Role does not exist')
        user.role = kwargs['role']
    
    if 'is_active' in kwargs:
        user.is_active = kwargs['is_active']
    
    db.session.commit()
    return user

def delete_user(user_id):
    """Delete a user by ID."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError('User not found')
    
    db.session.delete(user)
    db.session.commit()

def get_user(user_id):
    """Get a user by ID."""
    return User.query.get(user_id)

def list_users():
    """List all users."""
    return User.query.all()

def user_has_permission(user_id, permission_name):
    """Check if a user has a specific permission."""
    user = User.query.get(user_id)
    if not user:
        return False
    return user.has_permission(permission_name)
