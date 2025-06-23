from app import create_app, db

# Create a Flask app instance
app = create_app()

# Push an application context
with app.app_context():
    # Create all database tables
    db.create_all()
    print("Database tables created successfully.")
