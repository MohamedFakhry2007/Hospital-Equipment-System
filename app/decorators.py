from functools import wraps
from flask import jsonify, flash, redirect, request, url_for, abort
from flask_login import current_user
import logging

logger = logging.getLogger('app')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # For API requests, return JSON, else redirect to login
            if request.accept_mimetypes.accept_json and \
               not request.accept_mimetypes.accept_html:
                return jsonify({"message": "Authentication required."}), 401
            flash("You need to be logged in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))

        # Assuming user model has a 'role' attribute and role has a 'name' attribute
        if not hasattr(current_user, 'role') or current_user.role.name != 'Admin':
            logger.warning(f"Admin access denied for user {getattr(current_user, 'username', 'anonymous')}")
            if request.accept_mimetypes.accept_json and \
               not request.accept_mimetypes.accept_html:
                return jsonify(message="Admin access required."), 403 # Corrected: jsonify takes message kwarg
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # For API requests, return JSON, else redirect to login
                if request.accept_mimetypes.accept_json and \
                   not request.accept_mimetypes.accept_html:
                    return jsonify(message="Authentication required."), 401
                flash("You need to be logged in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.url))

            if not hasattr(current_user, 'role') or not current_user.role:
                # This case should ideally not happen for an authenticated user
                logger.warning(f"User {getattr(current_user, 'username', 'anonymous')} has no role assigned.")
                if request.accept_mimetypes.accept_json and \
                   not request.accept_mimetypes.accept_html:
                    return jsonify(message="User role not found."), 403
                abort(403)

            # Check if the user's role has the required permission
            has_permission = any(p.name == permission_name for p in current_user.role.permissions)

            if not has_permission:
                logger.warning(f"Permission denied for user {getattr(current_user, 'username', 'anonymous')} on {permission_name}")
                if request.accept_mimetypes.accept_json and \
                   not request.accept_mimetypes.accept_html:
                    return jsonify(message=f"Access Denied: You do not have the required permission '{permission_name}'."), 403
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
