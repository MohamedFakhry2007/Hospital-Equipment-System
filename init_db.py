"""
Initialize the database and create all tables.
Run this script once to set up the database.
"""
import os
from app import create_app, db
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.ocm import OCM
from app.models.ppm import PPM
from app.models.training import Training

def init_db():
    """Initialize the database and create all tables."""
    app = create_app()
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Create default roles if they don't exist
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            print("Created 'admin' role")
        
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Regular user with limited access')
            db.session.add(user_role)
            print("Created 'user' role")
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                role=admin_role
            )
            admin_user.set_password('admin')  # Default password, should be changed after first login
            db.session.add(admin_user)
            print("Created default admin user (username: 'admin', password: 'admin')")
        
        db.session.commit()
        print("Database initialization complete!")
        print(f"You can now log in with username: 'admin' and password: 'admin'")
        print("IMPORTANT: Please change the default password after logging in!")

if __name__ == '__main__':
    init_db()
