"""
Temporarily disabled admin routes.
These routes will be reimplemented to work with JSON-based authentication.
"""
from flask import Blueprint

# Create a dummy blueprint that does nothing
admin_bp = Blueprint('admin_bp', __name__)