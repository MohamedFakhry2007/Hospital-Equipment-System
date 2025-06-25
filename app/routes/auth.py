"""
Authentication routes for user login and logout.
"""
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db
from sqlalchemy.exc import OperationalError
from app.utils.logger_setup import setup_logger

# Set up logger for this module
logger = logging.getLogger('app')
logger.debug("[app.routes.auth] Logging started for auth.py")

auth_bp = Blueprint('auth', __name__)
logger.debug("[app.routes.auth] Auth blueprint initialized")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login requests."""
    logger.info("[app.routes.auth] Accessing login route")
    
    if current_user.is_authenticated:
        logger.info(f"[app.routes.auth] Authenticated user '{current_user.username}' redirected to index.")
        return redirect(url_for('views.index'))  # Redirect if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        logger.info(f"[app.routes.auth] Login attempt for username: {username}")

        try:
            user = User.query.filter_by(username=username).first()
            logger.debug(f"[app.routes.auth] Retrieved user: {user.username if user else 'None'}")

            if user and user.check_password(password):
                login_user(user)
                logger.info(f"[app.routes.auth] User '{username}' logged in successfully.")
                flash('Logged in successfully.', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('views.index'), code=303)
            else:
                logger.warning(f"[app.routes.auth] Failed login attempt for username: {username}")
                flash('Invalid username or password.', 'error')
        except OperationalError as e:
            logger.error(f"[app.routes.auth] Database connection error during login for username '{username}': {str(e)}")
            flash('Database connection error. Please contact the administrator.', 'error')
        except Exception as e:
            logger.exception(f"[app.routes.auth] Unexpected error during login for username '{username}': {str(e)}")
            flash('An unexpected error occurred. Please try again.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Handle user logout."""
    logger.info("[app.routes.auth] Accessing logout route")
    
    username = current_user.username if current_user.is_authenticated else "anonymous"
    logout_user()
    logger.info(f"[app.routes.auth] User '{username}' logged out.")
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))