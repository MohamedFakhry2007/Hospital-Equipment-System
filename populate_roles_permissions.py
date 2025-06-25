#!/usr/bin/env python3
"""
Script to populate initial roles and permissions for the Hospital Equipment System.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models.role import Role
from app.models.permission import Permission
from app.models.user import User

def populate_permissions():
    """Create the required permissions."""
    permissions = [
        'view_equipment',
        'manage_equipment', 
        'view_training',
        'manage_training',
        'view_audit_log',
        'manage_users',
        'manage_settings'
    ]
    
    created_permissions = []
    for perm_name in permissions:
        existing_perm = Permission.query.filter_by(name=perm_name).first()
        if not existing_perm:
            perm = Permission(name=perm_name)
            db.session.add(perm)
            created_permissions.append(perm_name)
            print(f"Created permission: {perm_name}")
        else:
            print(f"Permission already exists: {perm_name}")
    
    return created_permissions

def populate_roles():
    """Create the required roles and assign permissions."""
    # Define role-permission mappings
    role_permissions = {
        'Admin': [
            'view_equipment', 'manage_equipment', 'view_training', 'manage_training',
            'view_audit_log', 'manage_users', 'manage_settings'
        ],
        'Editor': [
            'view_equipment', 'manage_equipment', 'view_training', 'manage_training'
        ],
        'Viewer': [
            'view_equipment', 'view_training'
        ]
    }
    
    created_roles = []
    for role_name, perm_names in role_permissions.items():
        existing_role = Role.query.filter_by(name=role_name).first()
        if not existing_role:
            role = Role(name=role_name)
            db.session.add(role)
            db.session.flush()  # Flush to get the role ID
            
            # Assign permissions to role
            for perm_name in perm_names:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission:
                    role.permissions.append(permission)
                else:
                    print(f"Warning: Permission '{perm_name}' not found for role '{role_name}'")
            
            created_roles.append(role_name)
            print(f"Created role: {role_name} with permissions: {perm_names}")
        else:
            print(f"Role already exists: {role_name}")
            # Update permissions for existing role
            existing_permissions = [p.name for p in existing_role.permissions]
            for perm_name in perm_names:
                if perm_name not in existing_permissions:
                    permission = Permission.query.filter_by(name=perm_name).first()
                    if permission:
                        existing_role.permissions.append(permission)
                        print(f"Added permission '{perm_name}' to existing role '{role_name}'")
    
    return created_roles

def assign_admin_role_to_existing_users():
    """Assign Admin role to existing users who don't have a role."""
    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role:
        print("Error: Admin role not found!")
        return
    
    # Find users without a role or with the default role
    users_without_proper_role = User.query.filter(
        (User.role_id == None) | (User.role_id == 1)  # 1 is the default role from migration
    ).all()
    
    updated_users = []
    for user in users_without_proper_role:
        user.role_id = admin_role.id
        updated_users.append(user.username)
        print(f"Assigned Admin role to user: {user.username}")
    
    return updated_users

def main():
    """Main function to populate roles and permissions."""
    app = create_app()
    
    with app.app_context():
        print("Starting role and permission population...")
        
        # Create permissions
        print("\n1. Creating permissions...")
        created_permissions = populate_permissions()
        
        # Create roles and assign permissions
        print("\n2. Creating roles and assigning permissions...")
        created_roles = populate_roles()
        
        # Assign admin role to existing users
        print("\n3. Assigning Admin role to existing users...")
        updated_users = assign_admin_role_to_existing_users()
        
        # Commit all changes
        try:
            db.session.commit()
            print("\n✅ Successfully populated roles and permissions!")
            print(f"Created permissions: {created_permissions}")
            print(f"Created roles: {created_roles}")
            print(f"Updated users: {updated_users}")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {str(e)}")
            return 1
    
    return 0

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

