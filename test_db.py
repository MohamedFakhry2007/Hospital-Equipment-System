"""Test script to verify database setup and model registration."""
import os
from app import create_app
from app.extensions import db

def test_db_setup():
    """Test database setup and model registration."""
    # Create a test app
    os.environ['FLASK_ENV'] = 'development'
    app = create_app()
    
    # Push an application context
    with app.app_context():
        # Get all tables using SQLAlchemy 2.0+ compatible method
        from sqlalchemy import inspect, text
        
        # Get all tables using raw SQL (works across all SQLAlchemy versions)
        with db.engine.connect() as conn:
            if db.engine.url.drivername.startswith('sqlite'):
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
            else:
                # For other databases, use information_schema
                result = conn.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                ))
                tables = [row[0] for row in result]
            
            print("\nTables in database:")
            for table in tables:
                print(f"- {table}")
        
        # Check if PPMEquipment model is registered with SQLAlchemy
        print("\nModels in metadata:")
        for table_name in db.metadata.tables:
            print(f"- {table_name}")
        
        # Try to reflect the database to see all tables
        print("\nReflecting database...")
        db.reflect()
        print("Tables after reflection:")
        for table_name in db.metadata.tables:
            print(f"- {table_name}")
            
        # Check if we can query the PPMEquipment table directly
        try:
            from app.models.ppm_equipment import PPMEquipment
            print("\nAttempting to query PPMEquipment table...")
            count = db.session.query(PPMEquipment).count()
            print(f"Found {count} PPMEquipment records")
        except Exception as e:
            print(f"Error querying PPMEquipment: {e}")

if __name__ == "__main__":
    test_db_setup()
