import json
import os
import sys
from app import create_app, db
from app.models.user import User, Role, Permission
from werkzeug.security import generate_password_hash

def migrate_users():
    # Create app and ensure proper initialization
    app = create_app()
    
    # Ensure the app context is active
    with app.app_context():
        try:
            print("Creating database tables...")
            # Create all tables
            db.create_all()
            
            print("Loading settings from settings.json...")
            # Load existing settings
            settings_path = os.path.join(app.root_path, '..', 'data', 'settings.json')
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            print("Migrating roles and permissions...")
            # Migrate roles and permissions
            for role_name, role_data in settings.get('roles', {}).items():
                print(f"Processing role: {role_name}")
                role = Role.query.filter_by(name=role_name).first()
                if not role:
                    print(f"  - Creating new role: {role_name}")
                    role = Role(name=role_name)
                    db.session.add(role)
                    db.session.commit()
                
                # Add permissions
                for perm_name in role_data.get('permissions', []):
                    print(f"  - Processing permission: {perm_name}")
                    permission = Permission.query.filter_by(name=perm_name).first()
                    if not permission:
                        print(f"    - Creating new permission: {perm_name}")
                        permission = Permission(name=perm_name)
                        db.session.add(permission)
                        db.session.commit()
                    if permission not in role.permissions:
                        print(f"    - Adding permission {perm_name} to role {role_name}")
                        role.permissions.append(permission)
                db.session.commit()
            
            print("Migrating users...")
            # Migrate users
            for user_data in settings.get('users', []):
                username = user_data['username']
                print(f"Processing user: {username}")
                
                user = User.query.filter_by(username=username).first()
                if not user:
                    print(f"  - Creating new user: {username}")
                    # Ensure the role exists
                    role_name = user_data['role']
                    role = Role.query.filter_by(name=role_name).first()
                    if not role:
                        print(f"    - Role {role_name} not found, creating it")
                        role = Role(name=role_name)
                        db.session.add(role)
                        db.session.commit()

                    user = User(username=username)
                    user.role = role_name  # Store the role name as string

                    if user_data['password'].startswith(('scrypt:', '$2b$')):
                        user.password_hash = user_data['password']
                    else:
                        user.set_password(user_data['password'])

                    db.session.add(user)
                    db.session.commit()
                else:
                    print(f"  - User {username} already exists, skipping...")
            
            print("Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error during migration: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == '__main__':
    if migrate_users():
        sys.exit(0)
    else:
        sys.exit(1)