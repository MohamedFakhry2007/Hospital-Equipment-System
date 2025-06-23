from functools import wraps
from flask import jsonify
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"message": "Authentication required."}), 401
        # Assuming user model has a 'role' attribute and role has a 'name' attribute
        if not hasattr(current_user, 'role') or current_user.role.name != 'Admin':
            return jsonify({"message": "Admin access required."}), 403
        return f(*args, **kwargs)
    return decorated_function
