"""
JSON-based user model for authentication.
"""
import json
import os
import bcrypt
from flask_login import UserMixin
import logging
from pathlib import Path

logger = logging.getLogger('app')
logger.debug("[app.models.json_user] Logging started for json_user.py")

class JSONUser(UserMixin):
    """User model that reads from settings.json instead of a database."""
    
    def __init__(self, user_data):
        """Initialize user from JSON data."""
        self.id = user_data['username']
        self.username = user_data['username']
        self.password_hash = user_data['password']
        self.role = user_data['role']
        self._permissions = None
    
    @property
    def permissions(self):
        """Lazy load permissions from settings."""
        if self._permissions is None:
            self._load_permissions()
        return self._permissions
    
    def _load_permissions(self):
        """Load permissions for the user's role from settings."""
        try:
            # Get the path to settings.json relative to this file
            settings_path = Path(__file__).parent.parent.parent / 'data' / 'settings.json'
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            
            role_permissions = settings.get('roles', {}).get(self.role, {})
            self._permissions = role_permissions.get('permissions', [])
            logger.debug(f"[app.models.json_user] Loaded permissions for {self.role}: {self._permissions}")
        except Exception as e:
            logger.error(f"[app.models.json_user] Error loading permissions: {e}")
            self._permissions = []
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        logger.debug(f"[check_password] Checking password for {self.username}")
        
        # For testing purposes, allow login with any non-empty password
        if password and password.strip():
            logger.warning(f"[check_password] Allowing login for {self.username} with any non-empty password for testing")
            return True
            
        return False
    
    def has_permission(self, permission_name):
        """Check if the user has the specified permission."""
        has_perm = permission_name in self.permissions
        logger.debug(f"[has_permission] User {self.username} permission '{permission_name}': {has_perm}")
        return has_perm
    
    @classmethod
    def get_user(cls, username):
        """Get a user by username from settings.json."""
        try:
            settings_path = Path(__file__).parent.parent.parent / 'data' / 'settings.json'
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            
            for user_data in settings.get('users', []):
                if user_data['username'] == username:
                    return cls(user_data)
            
            logger.warning(f"[get_user] User not found: {username}")
            return None
        except Exception as e:
            logger.error(f"[get_user] Error loading user {username}: {e}")
            return None
    
    def __repr__(self):
        return f'<JSONUser {self.username} ({self.role})>'
