from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))  # Redirect if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            # Redirect to the page they were trying to access, or to index
            next_page = request.args.get('next')
            # Use 303 See Other to ensure the method changes to GET for the next request
            return redirect(next_page or url_for('views.index'), code=303)
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
# @login_required # Removed: logout should be accessible to logged-in users to log them out
def logout():
    logout_user()
    flash('You have been logged out.', 'success') # Changed category for clarity
    return redirect(url_for('auth.login'))
