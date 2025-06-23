from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    users = User.query.all()
    if not users:
        print("No users found in the database.")
    else:
        for user in users:
            print(f"Username: {user.username}")