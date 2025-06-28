from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from . import auth_bp
from werkzeug.security import check_password_hash

def check_password_stored_hash(stored_hash, password):
    """Check password against stored hash, handling different hash formats."""
    if not stored_hash or not password:
        return False
    
    # Handle scrypt format from settings.json
    if stored_hash.startswith('scrypt:'):
        from werkzeug.security import check_password_hash as werkzeug_check_hash
        try:
            # For scrypt hashes, we need to use the format 'scrypt:...'
            return werkzeug_check_hash(stored_hash, password)
        except Exception as e:
            print(f"Error checking scrypt hash: {e}")
            return False
    
    # Handle bcrypt format (if any)
    if stored_hash.startswith('$2b$'):
        from werkzeug.security import check_password_hash as werkzeug_check_hash
        try:
            return werkzeug_check_hash(stored_hash, password)
        except Exception:
            return False
    
    # Handle werkzeug format hashes (pbkdf2:sha256:...)
    try:
        from werkzeug.security import check_password_hash
        return check_password_hash(stored_hash, password)
    except Exception as e:
        print(f"Error checking password hash: {e}")
        return False

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    print("Login route accessed")  # Debug log
    if current_user.is_authenticated:
        print("User already authenticated, redirecting to index")  # Debug log
        return redirect(url_for('views.index'))
    
    if request.method == 'POST':
        print("Login POST request received")  # Debug log
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        print(f"Login attempt for user: {username}")  # Debug log
        
        # Try to get user from database first
        user = User.query.filter_by(username=username).first()
        
        # If user not found in database, try to load from settings.json
        if not user:
            print(f"User {username} not found in database, checking settings.json")  # Debug log
            from app.models.json_user import JSONUser
            user = JSONUser.get_user(username)
            if user:
                print(f"Found user {username} in settings.json")  # Debug log
                # Check password directly since we're using JSON user
                if not check_password_stored_hash(user.password_hash, password):
                    print(f"Invalid password for user {username}")  # Debug log
                    flash('Invalid username or password', 'error')
                    return redirect(url_for('auth.login'))
                
                # For JSON users, we don't have is_active check
                print(f"Logging in JSON user: {username}")  # Debug log
                login_user(user, remember=remember)
                return redirect(url_for('views.index'))
        
        # For database users
        if user:
            print(f"Found database user: {username}")  # Debug log
            # Check if user exists and password is correct
            if not check_password_stored_hash(user.password_hash, password):
                print(f"Invalid password for database user {username}")  # Debug log
                flash('Invalid username or password', 'error')
                return redirect(url_for('auth.login'))
            
            # Check if user is active
            if not user.is_active:
                print(f"Account {username} is disabled")  # Debug log
                flash('Account is disabled', 'error')
                return redirect(url_for('auth.login'))
            
            # Update password to new format if it was in old format
            if user.password_hash.startswith(('scrypt:', '$2b$')):
                print(f"Updating password hash format for user {username}")  # Debug log
                user.set_password(password)
                db.session.commit()
            
            # Log in the user
            print(f"Logging in database user: {username}")  # Debug log
            login_user(user, remember=remember)
            
            # Redirect to next page if it exists
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('views.index')
                
            return redirect(next_page)
        else:
            print(f"User {username} not found anywhere")  # Debug log
            flash('Invalid username or password', 'error')
            
    print("Rendering login template")  # Debug log
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
