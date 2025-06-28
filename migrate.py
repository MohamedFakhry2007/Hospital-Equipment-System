from app import create_app, db
from flask_migrate import Migrate, upgrade, migrate as _migrate, init, stamp
import os

def init_db():
    app = create_app()
    migrate = Migrate(app, db)
    
    with app.app_context():
        # Create migrations directory if it doesn't exist
        migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        if not os.path.exists(migrations_dir):
            init()
        
        # Create database tables
        db.create_all()
        
        # Create initial migration
        _migrate(message='Initial migration')
        
        # Apply the migration
        upgrade()
        
        print("Database initialized and migration applied successfully!")

if __name__ == '__main__':
    init_db()
