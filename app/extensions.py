from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    from app.models.json_user import JSONUser
    
    try:
        # First try to load as database user with numeric ID
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        # If that fails, try to load as JSON user with username
        return JSONUser.get_user(user_id)
