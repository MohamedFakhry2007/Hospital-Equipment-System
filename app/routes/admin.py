"""
Admin routes for managing users and roles.
"""
import logging
from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Role
from app.decorators import admin_required

# Set up logger for this module
logger = logging.getLogger('app')
logger.debug("[app.routes.admin] Logging started for admin.py")

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')
logger.debug("[app.routes.admin] Admin blueprint initialized with prefix '/admin'")


@admin_bp.route('/')
@admin_required
def admin_home():
    logger.info("[app.routes.admin] Accessing admin home route")
    return "Admin Dashboard"


@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    logger.info("[app.routes.admin] Creating new user via POST /users")
    data = request.get_json()
    if not data:
        logger.warning("[app.routes.admin] No input data provided during user creation")
        return jsonify({"message": "No input data provided"}), 400

    username = data.get('username')
    password = data.get('password')
    role_id = data.get('role_id')

    logger.debug(f"[app.routes.admin] Received data: username={username}, role_id={role_id}")

    if not all([username, password, role_id]):
        logger.warning("[app.routes.admin] Missing required fields during user creation")
        return jsonify({
            "message": "Missing data for required fields (username, password, role_id)"
        }), 400

    if User.query.filter_by(username=username).first():
        logger.warning(f"[app.routes.admin] Username '{username}' already exists")
        return jsonify({"message": "Username already exists"}), 409

    role = Role.query.get(role_id)
    if not role:
        logger.warning(f"[app.routes.admin] Role with ID {role_id} not found")
        return jsonify({"message": "Role not found"}), 404

    try:
        new_user = User(username=username, role_id=role_id)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        logger.info(f"[app.routes.admin] User '{new_user.username}' created successfully")
        user_data = {
            "id": new_user.id,
            "username": new_user.username,
            "role_id": new_user.role_id,
            "role": new_user.role.name
        }
        return jsonify(user_data), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"[app.routes.admin] Error creating user: {str(e)}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    logger.info("[app.routes.admin] Fetching list of all users")
    users = User.query.all()
    users_data = []

    for user in users:
        logger.debug(f"[app.routes.admin] Processing user: {user.username}")
        users_data.append({
            "id": user.id,
            "username": user.username,
            "role_id": user.role_id,
            "role": user.role.name if user.role else None
        })

    logger.info(f"[app.routes.admin] Retrieved {len(users_data)} users")
    return jsonify(users_data), 200


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    logger.info(f"[app.routes.admin] Updating user with ID {user_id}")
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        logger.warning("[app.routes.admin] No input data provided during user update")
        return jsonify({"message": "No input data provided"}), 400

    logger.debug(f"[app.routes.admin] Received update data: {data}")

    # Update username
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            logger.warning(f"[app.routes.admin] Username '{data['username']}' already taken")
            return jsonify({"message": "Username already exists"}), 409
        user.username = data['username']
        logger.debug(f"[app.routes.admin] Updated username to '{user.username}'")

    # Update password
    if 'password' in data and data['password']:
        user.set_password(data['password'])
        logger.debug("[app.routes.admin] Password updated for user")

    # Update role
    if 'role_id' in data:
        role = Role.query.get(data['role_id'])
        if not role:
            logger.warning(f"[app.routes.admin] Role with ID {data['role_id']} not found")
            return jsonify({"message": "Role not found"}), 404
        user.role_id = data['role_id']
        logger.debug(f"[app.routes.admin] Updated role_id to {user.role_id}")

    try:
        db.session.commit()
        logger.info(f"[app.routes.admin] User {user.id} updated successfully")
        updated_user_data = {
            "id": user.id,
            "username": user.username,
            "role_id": user.role_id,
            "role": user.role.name
        }
        return jsonify(updated_user_data), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"[app.routes.admin] Error updating user {user.id}: {str(e)}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    logger.info(f"[app.routes.admin] Deleting user with ID {user_id}")
    user = User.query.get_or_404(user_id)

    try:
        db.session.delete(user)
        db.session.commit()
        logger.info(f"[app.routes.admin] User {user_id} deleted successfully")
        return jsonify({"message": f"User with ID {user_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"[app.routes.admin] Error deleting user {user_id}: {str(e)}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500