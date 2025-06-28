from app import create_app
from app.extensions import db
from sqlalchemy import inspect

def check_database_schema():
    app = create_app()
    with app.app_context():
        # Initialize database
        db.create_all()
        
        # Get database inspector
        inspector = inspect(db.engine)
        
        # List all tables
        print("\nDatabase Tables:")
        tables = inspector.get_table_names()
        for table in tables:
            print(f"\nTable: {table}")
            
            # Get columns for each table
            columns = inspector.get_columns(table)
            print("  Columns:")
            for column in columns:
                print(f"    {column['name']}: {column['type']}")
            
            # Get indexes for each table
            indexes = inspector.get_indexes(table)
            if indexes:
                print("  Indexes:")
                for index in indexes:
                    print(f"    {index['name']}: {index['column_names']} (unique: {index.get('unique', False)})")

if __name__ == "__main__":
    check_database_schema()
