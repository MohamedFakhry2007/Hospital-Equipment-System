import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path("data/settings.json")

class PermissionManager:
    _permissions_cache = None

    @classmethod
    def _load_permissions(cls):
        if not SETTINGS_FILE.exists():
            logger.error(f"Settings file not found at {SETTINGS_FILE}")
            return {}
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            cls._permissions_cache = {role.lower(): set(perms.get('permissions', [])) 
                                      for role, perms in settings.get('roles', {}).items()}
            logger.info("Permissions loaded and cached.")
        except Exception as e:
            logger.error(f"Error loading permissions from {SETTINGS_FILE}: {e}")
            cls._permissions_cache = {}

    @classmethod
    def get_role_permissions(cls, role):
        if cls._permissions_cache is None:
            cls._load_permissions()
        return cls._permissions_cache.get(role.lower(), set())

    @classmethod
    def has_permission(cls, user_role, required_permission):
        if cls._permissions_cache is None:
            cls._load_permissions()
        
        # Admin role typically has all permissions, but it's good to explicitly check
        # if 'admin' in user_role.lower() and required_permission in cls._permissions_cache.get('admin', set()):
        #     return True

        return required_permission in cls.get_role_permissions(user_role)

    @classmethod
    def reload_permissions(cls):
        cls._permissions_cache = None # Invalidate cache
        cls._load_permissions() # Reload


