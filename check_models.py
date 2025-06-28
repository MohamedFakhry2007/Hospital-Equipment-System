"""Script to check database connection and model registration."""
import os
from app import create_app
from app.extensions import db

def check_models():
    """Check database connection and model registration."""
    # Set environment variables
    os.environ['FLASK_ENV'] = 'development'
    
    # Create app
    app = create_app()
    
    with app.app_context():
        print("=== Database Configuration ===")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Database file exists: {os.path.exists(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))}")
        
        # Check if tables exist
        from sqlalchemy import inspect, text
        
        # Connect to the database
        with db.engine.connect() as conn:
            # Check SQLite tables
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            
            print("\n=== Database Tables ===")
            for table in tables:
                print(f"- {table}")
        
        # Check SQLAlchemy metadata
        print("\n=== SQLAlchemy Metadata ===")
        db.reflect()
        for table_name in db.metadata.tables:
            print(f"- {table_name}")
        
        # Try to import and check PPMEquipment model
        try:
            from app.models.ppm_equipment import PPMEquipment
            print("\n=== PPMEquipment Model ===")
            print(f"Table name: {PPMEquipment.__tablename__}")
            print(f"Columns: {[c.name for c in PPMEquipment.__table__.columns]}")
            
            # Try to query the table
            count = db.session.query(PPMEquipment).count()
            print(f"Number of records: {count}")
            
        except Exception as e:
            print(f"\nError with PPMEquipment model: {e}")

if __name__ == "__main__":
    check_models()
