from app import create_app, db
from app.models import User, Role, Permission # Adjusted import to use app.models

def populate_data():
    """
    Populates the database with initial roles, permissions, and their mappings.
    This script should be run within the Flask application context.
    Example:
    flask shell
    >>> from populate_initial_data import populate_data
    >>> populate_data()
    """
    app = create_app()
    with app.app_context():
        # --- Permissions ---
        permissions_list = [
            # Dashboard
            "View Dashboard",
            # PPM
            "View PPM Equipment", "Create/Edit/Delete PPM Equipment", "Download PPM Template",
            "Import PPM in Bulk", "Export all PPM machines", "Generate PPM Barcode",
            "Print PPM Machine Barcode", "View/Print PPM History Log", "Edit PPM Status in Table",
            # OCM
            "View OCM Equipment", "Create/Edit/Delete OCM Equipment", "Download OCM Template",
            "Import OCM in Bulk", "Export all OCM machines", "Generate OCM Barcode",
            "Print OCM Machine Barcode", "View/Print OCM History Log", "Edit OCM Status in Table",
            # Training
            "View Training Records", "Create/Edit/Delete Training Records",
            "View/Print Training History Log", # Combined "Edit/Delete Training Records" as it's covered by Create/Edit/Delete
            # Reports
            "View/Save/Print/Download Reports",
            # Import & Export
            "Import/Export Data",
            # Audit
            "View Audit Logs",
            # Settings
            "User Management", "View/Edit Settings", "Theme Management", "Bulk operations on equipment"
        ]

        permission_objects = {}
        for perm_name in permissions_list:
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name)
                db.session.add(perm)
            permission_objects[perm_name] = perm
        db.session.commit()
        print("Permissions populated.")

        # --- Roles ---
        roles_data = {
            "Admin": [
                # Dashboard
                "View Dashboard",
                # PPM
                "View PPM Equipment", "Create/Edit/Delete PPM Equipment", "Download PPM Template",
                "Import PPM in Bulk", "Export all PPM machines", "Generate PPM Barcode",
                "Print PPM Machine Barcode", "View/Print PPM History Log", "Edit PPM Status in Table",
                # OCM
                "View OCM Equipment", "Create/Edit/Delete OCM Equipment", "Download OCM Template",
                "Import OCM in Bulk", "Export all OCM machines", "Generate OCM Barcode",
                "Print OCM Machine Barcode", "View/Print OCM History Log", "Edit OCM Status in Table",
                # Training
                "View Training Records", "Create/Edit/Delete Training Records", "View/Print Training History Log",
                # Reports
                "View/Save/Print/Download Reports",
                # Import & Export
                "Import/Export Data",
                # Audit
                "View Audit Logs",
                # Settings
                "User Management", "View/Edit Settings", "Theme Management", "Bulk operations on equipment"
            ],
            "Editor": [
                # Dashboard
                "View Dashboard",
                # PPM
                "View PPM Equipment", "Create/Edit/Delete PPM Equipment", "Download PPM Template",
                "Import PPM in Bulk", "Export all PPM machines", "Generate PPM Barcode",
                "Print PPM Machine Barcode", "View/Print PPM History Log", "Edit PPM Status in Table",
                # OCM
                "View OCM Equipment", "Create/Edit/Delete OCM Equipment", "Download OCM Template",
                "Import OCM in Bulk", "Export all OCM machines", "Generate OCM Barcode",
                "Print OCM Machine Barcode", "View/Print OCM History Log", "Edit OCM Status in Table",
                # Training
                "View Training Records", "Create/Edit/Delete Training Records", "View/Print Training History Log",
                # Reports
                "View/Save/Print/Download Reports",
                # Import & Export
                "Import/Export Data",
                # Settings
                "Theme Management"
            ],
            "Viewer": [
                # Dashboard
                "View Dashboard",
                # PPM
                "View PPM Equipment",
                # OCM
                "View OCM Equipment",
                # Settings
                "Theme Management"
            ]
        }

        for role_name, perm_names in roles_data.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name)
                db.session.add(role)

            role.permissions.clear() # Clear existing permissions before adding new ones
            for perm_name in perm_names:
                perm = permission_objects.get(perm_name)
                if perm and perm not in role.permissions:
                    role.permissions.append(perm)

        db.session.commit()
        print("Roles and Role-Permission mappings populated.")

        print("Initial data population complete.")
        print("To run this script:")
        print("1. Ensure your Flask app environment is set up (e.g., FLASK_APP is defined).")
        print("2. Open Flask shell: `flask shell`")
        print("3. In the shell, run: ")
        print("   >>> from populate_initial_data import populate_data")
        print("   >>> populate_data()")

if __name__ == '__main__':
    # This allows running the script directly if the Flask app context can be set up.
    # However, using `flask shell` is often more reliable for db operations.
    print("This script is intended to be run within a Flask application context.")
    print("Please use 'flask shell' and then call the populate_data() function.")
    print("Example:")
    print("  flask shell")
    print("  >>> from populate_initial_data import populate_data")
    print("  >>> populate_data()")
    # For direct execution to work, FLASK_APP needs to be configured,
    # and create_app() must be callable without arguments or with defaults.
    # try:
    #     populate_data()
    # except Exception as e:
    #     print(f"Error during direct execution: {e}")
    #     print("Consider running within 'flask shell' for proper app context.")
