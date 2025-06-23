from flask import Blueprint

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

from flask import request, jsonify
from app import db
from app.models import User, Role
from app.decorators import admin_required # Import the decorator

# Placeholder for admin-only routes
@admin_bp.route('/')
@admin_required
def admin_home():
    return "Admin Dashboard"

@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    username = data.get('username')
    # email = data.get('email') # Email field not in User model
    password = data.get('password')
    role_id = data.get('role_id')

    if not all([username, password, role_id]): # Email removed from check
        return jsonify({"message": "Missing data for required fields (username, password, role_id)"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 409

    # if User.query.filter_by(email=email).first(): # Email field not in User model
    #     return jsonify({"message": "Email already exists"}), 409

    role = Role.query.get(role_id)
    if not role:
        return jsonify({"message": "Role not found"}), 404

    new_user = User(username=username, role_id=role_id) # Email removed
    new_user.set_password(password) # Use the model's method
    db.session.add(new_user)
    db.session.commit()

    # Prepare response data, excluding password
    user_data = {
        "id": new_user.id,
        "username": new_user.username,
        # "email": new_user.email, # Email field not in User model
        "role_id": new_user.role_id,
        "role": new_user.role.name
    }
    return jsonify(user_data), 201

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    users = User.query.all()
    users_data = []
    for user in users:
        users_data.append({
            "id": user.id,
            "username": user.username,
            # "email": user.email, # Email field not in User model
            "role_id": user.role_id,
            "role": user.role.name if user.role else None # Handle case where role might be None, though schema says nullable=False
        })
    return jsonify(users_data), 200

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        return jsonify({"message": "No input data provided"}), 400

    # Update username if provided and different from current
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"message": "Username already exists"}), 409
        user.username = data['username']

    # Update email if provided and different from current - User model does not have email yet
    # if 'email' in data and data['email'] != user.email:
    #     if User.query.filter_by(email=data['email']).first():
    #         return jsonify({"message": "Email already exists"}), 409
    #     user.email = data['email']

    # Update password if provided
    if 'password' in data and data['password']: # Ensure password is not empty
        user.set_password(data['password'])

    # Update role if provided
    if 'role_id' in data:
        role = Role.query.get(data['role_id'])
        if not role:
            return jsonify({"message": "Role not found"}), 404
        user.role_id = data['role_id']

    db.session.commit()

    updated_user_data = {
        "id": user.id,
        "username": user.username,
        # "email": user.email, # Email field not in User model
        "role_id": user.role_id,
        "role": user.role.name
    }
    return jsonify(updated_user_data), 200

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Optional: Prevent deleting oneself or a super-admin, though not specified in requirements yet
    # For example:
    # current_user_id = get_jwt_identity() # Assuming JWT and a way to get current user
    # if user.id == current_user_id:
    #     return jsonify({"message": "Cannot delete yourself"}), 403
    # if user.role.name == 'SuperAdmin': # Or some other protected role
    #    return jsonify({"message": "Cannot delete a SuperAdmin user"}), 403

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User with ID {user_id} deleted successfully"}), 200
