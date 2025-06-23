import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db
from sqlalchemy.exc import OperationalError
from app.utils.logger_setup import setup_logger

# Use the centralized app logger
logger = logging.getLogger('app')

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logger.info("Authenticated user redirected to index.")
        return redirect(url_for('views.index'))  # Redirect if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user)
                logger.info(f"User '{username}' logged in successfully.")
                flash('Logged in successfully.', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('views.index'), code=303)
            else:
                logger.info(f"Failed login attempt for username: {username}")
                flash('Invalid username or password.', 'error')
        except OperationalError as e:
            logger.error(f"Database connection error during login: {str(e)}")
            flash('Database connection error. Please contact the administrator.', 'error')
        except Exception as e:
            logger.exception("Unexpected error during login:")
            flash('An unexpected error occurred. Please try again.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    username = current_user.username if current_user.is_authenticated else "anonymous"
    logout_user()
    logger.info(f"User '{username}' logged out.")
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))