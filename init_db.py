"""
Initialize the database and create all tables.
Run this script once to set up the database.
"""
import os
from datetime import datetime

from app import create_app, db
from app.models.user import User, Role, Permission
from app.models.ppm_equipment import PPMEquipment

def init_db():
    """Initialize the database and create all tables."""
    app = create_app()
    with app.app_context():
        # Drop all tables (be careful with this in production!)
        db.drop_all()
        
        # Create all database tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Create default permissions if they don't exist
        permissions = [
            'manage_users', 'manage_equipment', 'view_reports',
            'schedule_maintenance', 'perform_maintenance'
        ]
        
        for perm_name in permissions:
            if not Permission.query.filter_by(name=perm_name).first():
                db.session.add(Permission(name=perm_name))
        
        # Create default roles if they don't exist
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            print("Created 'admin' role")
        
        # Add all permissions to admin role
        all_perms = Permission.query.all()
        admin_role.permissions = all_perms
        
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user')
            db.session.add(user_role)
            print("Created 'user' role")
            
            # Add basic permissions to user role
            view_perm = Permission.query.filter_by(name='view_reports').first()
            if view_perm:
                user_role.permissions.append(view_perm)
        
        # Create default admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            print("Created default admin user (username: admin, password: admin123)")
        
        db.session.commit()
        print("Database initialization complete!")
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
