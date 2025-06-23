import os
from getpass import getpass
from app import create_app, db
from app.models.user import User

def main():
    """Creates an admin user."""
    app = create_app()
    with app.app_context():
        print("Creating admin user...")
        username = input("Enter admin username: ")
        password = getpass("Enter admin password: ")
        confirm_password = getpass("Confirm admin password: ")

        if password != confirm_password:
            print("Passwords do not match. Admin user not created.")
            return

        if User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists. Admin user not created.")
            return

        admin_user = User(username=username)
        admin_user.set_password(password)

        try:
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user '{username}' created successfully.")
            print("You can now log in with these credentials.")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {e}")

if __name__ == '__main__':
    # Check if running in a CI environment or non-interactive shell
    if not os.isatty(0) or os.getenv('CI'):
        print("Non-interactive environment detected. Attempting to create default admin.")
        app = create_app()
        with app.app_context():
            default_username = "admin"
            default_password = "changeme" # Standard practice to use a known default for CI

            if User.query.filter_by(username=default_username).first():
                print(f"Default admin user '{default_username}' already exists.")
            else:
                admin_user = User(username=default_username)
                admin_user.set_password(default_password)
                try:
                    db.session.add(admin_user)
                    db.session.commit()
                    print(f"Default admin user '{default_username}' created with password '{default_password}'.")
                    print("IMPORTANT: Change this password immediately in a production environment!")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error creating default admin user: {e}")
    else:
        main()
