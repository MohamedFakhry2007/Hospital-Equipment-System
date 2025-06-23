from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    username = "admin"
    password = "changeme"
    if User.query.filter_by(username=username).first():
        print(f"User '{username}' already exists.")
    else:
        admin_user = User(username=username)
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user '{username}' created with password '{password}'.") 