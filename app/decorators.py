"""
Decorators for access control and authentication.
"""
from functools import wraps
from flask import jsonify, flash, redirect, request, url_for, abort
from flask_login import current_user
import logging

logger = logging.getLogger('app')
logger.debug("[app.decorators] Logging started for decorators.py")

def admin_required(f):
    """Decorator to restrict access to admin users only."""
    return permission_required('manage_users')(f)


def permission_required(permission_name):
    """Decorator to restrict access based on specific permissions."""
    logger.debug(f"[app.decorators] Applying permission_required decorator for permission: {permission_name}")
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.debug(f"[app.decorators] Checking permission: {permission_name}")
            if not current_user.is_authenticated:
                logger.warning("[app.decorators] Unauthenticated user attempted access")
                if request.accept_mimetypes.accept_json and \
                   not request.accept_mimetypes.accept_html:
                    logger.debug("[app.decorators] Returning JSON response for unauthenticated access")
                    return jsonify(message="Authentication required."), 401
                flash("You need to be logged in to access this page.", "warning")
                logger.info("[app.decorators] Redirecting unauthenticated user to login page")
                return redirect(url_for("auth.login", next=request.url))

            if not hasattr(current_user, "role") or not current_user.role:
                logger.warning(f"[app.decorators] User {getattr(current_user, 'username', 'anonymous')} has no role assigned")
                if request.accept_mimetypes.accept_json and \
                   not request.accept_mimetypes.accept_html:
                    logger.debug("[app.decorators] Returning JSON response for no role assigned")
                    return jsonify(message="User role not found."), 403
                logger.info("[app.decorators] Aborting with 403 for user with no role")
                abort(403)

            # Check if the user's role has the required permission
            if isinstance(permission_name, (list, tuple)):
                # If multiple permissions are provided, check if user has any of them
                has_permission = any(perm in current_user.permissions for perm in permission_name)
            else:
                # Single permission check
                has_permission = permission_name in current_user.permissions
                
            logger.debug(f"[app.decorators] Permission check result for {permission_name}: {has_permission}")

            if not has_permission:
                logger.warning(f"[app.decorators] Permission denied for user {getattr(current_user, 'username', 'anonymous')} on {permission_name}")
                if request.accept_mimetypes.accept_json and \
                   not request.accept_mimetypes.accept_html:
                    logger.debug("[app.decorators] Returning JSON response for permission denied")
                    return jsonify(message=f"Access Denied: You do not have the required permission '{permission_name}'."), 403
                logger.info("[app.decorators] Aborting with 403 for insufficient permissions")
                abort(403)

            logger.debug("[app.decorators] Permission granted")
            return f(*args, **kwargs)
        return decorated_function
    return decorator
